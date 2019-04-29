from graphql.pyutils.cached_property import cached_property
from umongo.frameworks.tools import cook_find_filter
from umongo.template import Template

from .utils import iter_umongo_fields


class UMongoBaseQueryset:
    model = None
    collection_name = None
    embedded_documents_field = None
    documents_converter = None

    def __init__(self, model,
                 collection_name=None,
                 embedded_documents_field=None,
                 documents_converter=None):
        super().__init__()
        self.model = model
        self.embedded_documents_field = embedded_documents_field
        self.documents_converter = documents_converter or self.model.build_from_mongo

        if collection_name:
            self.collection_name = collection_name
        elif hasattr(model.opts, 'collection_name'):
            self.collection_name = model.opts.collection_name

        assert isinstance(self.collection_name, str), self.collection_name
        assert callable(self.documents_converter) or self.documents_converter is None

    def get_fields(self):
        return ((n, f) for n, f in iter_umongo_fields(
            self.model.opts.template
        ))

    def get_field_names(self, deep=False, parent_field=None):
        def _iter_fields(m, deep, parent_field):
            template = m if issubclass(m, Template) else m.opts.template
            for n, f in iter_umongo_fields(template):
                if deep and hasattr(f, 'container'):
                    if hasattr(f.container, 'embedded_document'):
                        yield from _iter_fields(
                            f.container.embedded_document, deep, n
                        )
                yield f'{parent_field}.{n}' if parent_field else n
        return (f for f in _iter_fields(self.model, deep, parent_field))

    def get_pk(self):
        for n, f in self.get_fields():
            if (n == '_id' and not f.attribute) or f.attribute == '_id':
                return n, f
        raise Exception(
            f'No primary key found in {self.model.__class__.__name__}'
        )

    @cached_property
    def base_projection(self):
        return {}

    @cached_property
    def collection(self):
        return self.model.opts.instance.db[self.collection_name]

    async def find(self, match, projection, limit, skip):
        raise NotImplementedError

    async def find_one(self, match, projection, limit, skip):
        raise NotImplementedError


class UMongoFindQueryset(UMongoBaseQueryset):
    async def find(self, match, projections, limit=0, skip=0):
        _projections = self.base_projection
        if projections:
            _projections.update(projections)

        cursor = self.collection.find(
            filter=match,
            projection=_projections,
            limit=limit,
            skip=skip)
        return [self.documents_converter(document)
                async for document in cursor]

    async def find_one(self, match, projections):
        _projections = self.base_projection
        if projections:
            _projections.update(projections)

        return self.documents_converter(await self.collection.find_one(
            filter=match,
            projection=_projections))


class UMongoAggregationQueryset(UMongoBaseQueryset):
    @classmethod
    def _get_match(cls, kwargs, list_field=None):
        match = dict()
        for key, value in kwargs.items():
            _key = f'{list_field}.{key}' if list_field else key
            if isinstance(value, list):
                match[_key] = {'$in': value}
            else:
                match[_key] = value
        return match

    @classmethod
    def _get_projection(cls, match, projections, list_field=None):
        _projections = dict()
        for key, value in projections.items():
            if list_field and key == list_field:
                _projections[key] = value
            else:
                _projections[key] = value
        return _projections

    @classmethod
    def _get_unwind_stages(cls, docs_field):
        unwind_path = list()
        unwind_stages = list()
        for i in docs_field.split('.'):
            unwind_path.append(i)
            unwind_stages.append({
                '$unwind': {'path': f"${'.'.join(unwind_path)}"}
            })
        return unwind_stages

    def _get_aggregation_pipeline(self, docs_field, match, projections, limit=0, skip=0):
        pipeline = list()
        pipeline.append({'$match': self._get_match(match, docs_field)})
        if docs_field:
            pipeline.extend(self._get_unwind_stages(docs_field))
            pipeline.append({'$replaceRoot': {'newRoot': f'${docs_field}'}})
            pipeline.append({'$match': self._get_match(match)})
        if skip:
            pipeline.append({'$skip': skip})
        if limit:
            pipeline.append({'$limit': limit})
        if projections and len(projections):
            pipeline.append({'$project': self._get_projection(
                match, projections, docs_field)
            })
        return pipeline

    async def find(self, match, projections, limit=0, skip=0):
        _projections = self.base_projection
        if projections:
            _projections.update(projections)

        cursor = self.collection.aggregate(self._get_aggregation_pipeline(
            self.embedded_documents_field,
            cook_find_filter(self.model, match),
            _projections,
            limit,
            skip
        ))
        return [self.documents_converter(doc) async for doc in cursor]

    async def find_one(self, match, projections):
        return next(iter(await self.find(match, projections)), None)
