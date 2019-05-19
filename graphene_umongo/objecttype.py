import graphene
import umongo

from .converter import (get_attributes_fields, convert_umongo_model,
                        convert_model_to_attributes)
from .querysets import FindQueryset, init_queryset
from .registry import Registry, get_global_registry
from .utils import (get_query, iter_fields, _get_embedded_field_model_class,
                    _iter_umongo_model_offspring)


class ObjectTypeOptions(graphene.types.objecttype.ObjectTypeOptions):
    model = None
    registry = None
    connection = None
    field_names_convertor = None
    field_types_convertor = None
    attributes = None
    id = None


class ObjectType(graphene.ObjectType):
    @classmethod
    def __init_subclass_with_meta__(
        cls,
        model=None,
        attributes=None,
        queryset=None,
        registry=None,
        skip_registry=False,
        only_fields=(),
        exclude_fields=(),
        connection=None,
        connection_class=None,
        use_connection=None,
        interfaces=(),
        id=None,
        _meta=None,
        **options
    ):
        assert issubclass(model, umongo.document.DocumentImplementation),\
            f'You need to pass a valid uMongo Model in "{cls.__name__}", ' \
            f'received "{model}", {model.__bases__}'

        if not registry:
            registry = get_global_registry()
        assert isinstance(registry, Registry), f'The attribute registry in ' \
            f'{cls.__name__} needs to be an instance of Registry, received ' \
            f'\'{registry}\'.'

        if not attributes:
            attributes = convert_model_to_attributes(model)

        if not queryset:
            queryset = FindQueryset

        queryset = init_queryset(queryset, model, cls)
        registry.register_queryset(model, queryset)
        assert registry.get_queryset(model) == queryset

        if use_connection is None and interfaces:
            use_connection = any(
                (issubclass(interface, graphene.relay.Node)
                 for interface in interfaces)
            )

        if use_connection and not connection:
            # We create the connection automatically
            if not connection_class:
                connection_class = graphene.relay.Connection
            connection = connection_class.create_type(
                f'{cls.__name__}Connection', node=cls
            )

        if connection is not None:
            assert issubclass(connection, graphene.relay.Connection),\
                f'The connection must be a Connection.' \
                f'Received {connection.__name__}'

        if not _meta:
            _meta = ObjectTypeOptions(cls)

        _meta.model = model
        _meta.registry = registry
        _meta.connection = connection
        _meta.attributes = attributes
        _meta.field_names_convertor = cls._get_field_names_convertor(model)
        _meta.field_types_convertor = cls._get_field_types_convertor(model)
        _meta.id = id or "id"

        _fields = {
            n: getattr(attributes, n) for n in dir(attributes)
            if (not callable(getattr(attributes, n)) and
                not n.startswith('__'))
        }
        _fields.update(get_attributes_fields(model, registry))

        if _meta.fields:
            _meta.fields.update(_fields)
        else:
            _meta.fields = _fields

        super(ObjectType, cls).__init_subclass_with_meta__(
            _meta=_meta, interfaces=interfaces, **options
        )

        if not skip_registry:
            registry.register(cls)

    @classmethod
    def is_type_of(cls, root, info):
        if isinstance(root, cls):
            return True
        return isinstance(root, cls._meta.model)

    @classmethod
    async def get_query(cls, info):
        model = cls._meta.model
        reg = get_global_registry()
        queryset = reg.get_queryset(model)
        return await get_query(model, queryset.find_one, info)

    @classmethod
    async def get_node(cls, info, id):
        return await cls.get_query(info)

    @classmethod
    async def postprocess_db_response(cls, document):
        if not document:
            return None

        def _convert_embed_doc(document, converter):
            assert isinstance(converter, list)
            result = document
            for i in converter:
                try:
                    result = i(**result)
                except Exception as _:
                    continue
                else:
                    break
            return result

        def _convert_document(document, converter):
            fields = {}
            for k, v in document.items():
                conv = converter.get(k)
                if isinstance(conv, str):
                    fields[conv] = v
                elif isinstance(conv, dict):
                    embed_conv = cls._meta.field_types_convertor.get(k)
                    assert embed_conv
                    if isinstance(v, list):
                        fields[k] = [
                            _convert_embed_doc(
                                _convert_document(d, conv), embed_conv)
                            for d in v]
                    else:
                        fields[k] = _convert_embed_doc(
                            _convert_document(v, conv), embed_conv)
            return fields

        return cls(**_convert_document(
            document, cls._meta.field_names_convertor))

    @classmethod
    def _get_field_names_convertor(cls, model):
        def _from_mongo_world(i):
            if i == '_id':
                return 'id'
            return i

        def _collect_fields(model, registry):
            _result = {}
            for _, n, f in iter_fields(model):
                mongo_field = f.attribute or n
                embedded_doc = _get_embedded_field_model_class(f)
                if embedded_doc:
                    _embed_fields = _collect_fields(embedded_doc, registry)
                    for o in _iter_umongo_model_offspring(embedded_doc):
                        _embed_fields.update(_collect_fields(o, registry))
                    _result[mongo_field] = _embed_fields
                else:
                    _result[mongo_field] = _from_mongo_world(mongo_field)
            return _result

        _conv = {'_id': 'id'}
        _conv.update(_collect_fields(model, get_global_registry()))
        return _conv

    @classmethod
    def _get_field_types_convertor(cls, model):
        def _collect_converters(model, registry):
            _result = {}
            for _, n, f in iter_fields(model):
                embedded_doc = _get_embedded_field_model_class(f)
                if embedded_doc:
                    _result[n] = [
                        convert_umongo_model(o, registry)
                        for o in _iter_umongo_model_offspring(embedded_doc)
                    ]
            return _result

        _conv = {}
        _conv.update(_collect_converters(model, get_global_registry()))
        return _conv
