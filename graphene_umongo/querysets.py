import umongo
from graphql.pyutils.cached_property import cached_property

from .utils import iter_fields, _get_umongo_mongo_world_fields


def init_queryset(queryset_cls, model, schema_cls):
    def _find_collection(m):
        try:
            if hasattr(m, 'collection'):
                return m.collection
        except umongo.exceptions.NoDBDefinedError:
            pass

        if hasattr(m, 'opts'):
            if hasattr(m.opts, 'collection_name'):
                return m.opts.collection_name
            if hasattr(m.opts, 'offspring') and len(m.opts.offspring):
                return _find_collection(next(iter(m.opts.offspring)))

        if hasattr(m, 'Meta'):
            if hasattr(m.Meta, 'collection_name'):
                return m.Meta.collection_name
            if hasattr(m.Meta, 'offspring') and len(m.Meta.offspring):
                return _find_collection(next(iter(m.Meta.offspring)))

        return model.__name__.lower()

    def _find_container_field(m, collection):
        return None

    collection = _find_collection(model)
    container = _find_container_field(model, collection)
    assert collection, model

    return queryset_cls(model,
                        getattr(collection, 'name', collection),
                        container,
                        getattr(schema_cls, 'postprocess_db_response', None))


class BaseQueryset:
    model = None
    collection_name = None
    embedded_documents_field = None
    documents_converter = None

    def __init__(self, model,
                 collection_name=None,
                 embedded_docs_field=None,
                 doc_converter=None):
        super().__init__()
        self.model = model
        self.embedded_documents_field = embedded_docs_field
        self.documents_converter = doc_converter

        if collection_name:
            self.collection_name = collection_name
        elif hasattr(model, 'opts') and hasattr(model.opts, 'collection_name'):
            self.collection_name = model.opts.collection_name
        elif hasattr(model, 'Meta') and hasattr(model.Meta, 'collection_name'):
            self.collection_name = model.Meta.collection_name

        assert isinstance(self.collection_name, str), self.collection_name
        assert callable(self.documents_converter) or self.documents_converter is None

    def get_fields(self):
        return ((n, f) for n, _, f in iter_fields(self.model))

    def get_pk(self):
        for n, f in self.get_fields():
            if (n == '_id' and not f.attribute) or f.attribute == '_id':
                return n, f
        raise Exception(
            f'No primary key found in {self.model.__class__.__name__}'
        )

    @cached_property
    def base_projection(self):
        return NotImplementedError

    @cached_property
    def collection(self):
        return self.model.opts.instance.db[self.collection_name]

    async def find(self, match, projection, limit, skip):
        raise NotImplementedError

    async def find_one(self, match, projection):
        raise NotImplementedError


class FindQueryset(BaseQueryset):
    def get_field_names(self):
        return (f for f, _, _ in iter_fields(self.model, deep=True))

    @cached_property
    def base_projection(self):
        _projections = {}
        _python_fields = _get_umongo_mongo_world_fields(self.model)
        for k, v in _python_fields.items():
            _projections[k] = True
        return _projections

    async def find(self, match={}, projections={}, limit=0, skip=0):
        _projections = self.base_projection
        _projections.update(projections)

        cursor = self.collection.find(
            filter=match,
            projection=_projections,
            limit=limit,
            skip=skip)

        if self.documents_converter:
            _documents = [self.documents_converter(document)
                          async for document in cursor]
        else:
            _documents = [document
                          async for document in cursor]

        return _documents

    async def find_one(self, match={}, projections={}):
        _projections = self.base_projection
        _projections.update(projections)

        _result = await self.collection.find_one(
            filter=match,
            projection=_projections)

        if self.documents_converter:
            _result = self.documents_converter(_result)

        return _result
