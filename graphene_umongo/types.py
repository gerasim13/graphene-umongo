
from collections import OrderedDict

from graphene import Field
from graphene.relay import Connection, Node
from graphene.types.objecttype import ObjectType, ObjectTypeOptions
from graphene.types.utils import yank_fields_from_attrs

from umongo.exceptions import NoDBDefinedError
from umongo.template import Template
from .converter import convert_umongo_field
from .querysets import UMongoBaseQueryset, UMongoFindQueryset
from .registry import Registry, get_global_registry
from .utils import iter_umongo_fields


def construct_fields(model, registry, only_fields, exclude_fields):
    fields = OrderedDict()
    for name, field in iter_umongo_fields(model):
        fields[name] = convert_umongo_field(field, registry)
    return fields


def init_queryset(queryset_cls, model, schema_cls):
    def _find_collection(m):
        try:
            if hasattr(m, 'collection'):
                return m.collection
        except NoDBDefinedError:
            pass

        if hasattr(m, 'opts'):
            if hasattr(m.opts, 'collection_name'):
                return m.opts.collection_name
            if hasattr(m.opts, 'offspring') and len(m.opts.offspring):
                return _find_collection(next(iter(m.opts.offspring)))

        return None

    def _find_container_field(m):
        pass

    _collection = _find_collection(model)
    if not _collection:
        return None

    return queryset_cls(
        model, _collection,
        _find_container_field(model),
        schema_cls.postprocess_db_response)


class UMongoObjectTypeOptions(ObjectTypeOptions):
    model = None
    queryset = None
    registry = None
    connection = None
    id = None


class UMongoObjectType(ObjectType):
    @classmethod
    def __init_subclass_with_meta__(
        cls,
        model=None,
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
        if not queryset:
            queryset = UMongoFindQueryset
        assert issubclass(queryset, UMongoBaseQueryset), f'You need to pass ' \
            f'a valid queryset class, subclass of {UMongoBaseQueryset}, ' \
            f'received \'{queryset}\''
        queryset = init_queryset(queryset, model, cls)

        if not issubclass(model, Template) and hasattr(model, 'opts'):
            model = model.opts.template
        else:
            raise Exception('Invalid model provided')
        assert issubclass(model, Template), f'You need to pass a valid ' \
            f'uMongo Model in \'{cls.__name__}\', received \'{model}\''

        if not registry:
            registry = get_global_registry()
        assert isinstance(registry, Registry), f'The attribute registry in ' \
            f'{cls.__name__} needs to be an instance of Registry, received ' \
            f'\'{registry}\'.'

        _fields = yank_fields_from_attrs(
            construct_fields(model, registry, only_fields, exclude_fields),
            _as=Field
        )

        if use_connection is None and interfaces:
            use_connection = any(
                (issubclass(interface, Node) for interface in interfaces)
            )

        if use_connection and not connection:
            # We create the connection automatically
            if not connection_class:
                connection_class = Connection

            connection = connection_class.create_type(
                f'{cls.__name__} connection', node=cls
            )

        if connection is not None:
            assert issubclass(connection, Connection), f'The connection ' \
                f'must be a Connection. Received {connection.__name__}'

        if not _meta:
            _meta = UMongoObjectTypeOptions(cls)

        _meta.model = model
        _meta.registry = registry
        _meta.connection = connection
        _meta.queryset = queryset
        _meta.id = id or "id"

        if _meta.fields:
            _meta.fields.update(_fields)
        else:
            _meta.fields = _fields

        super(UMongoObjectType, cls).__init_subclass_with_meta__(
            _meta=_meta, interfaces=interfaces, **options
        )

        if not skip_registry:
            registry.register(cls)

    @classmethod
    def is_type_of(cls, root, info):
        if isinstance(root, cls):
            return True
        if not is_mapped_instance(root):
            raise Exception(f'Received incompatible instance "{root}".')
        return isinstance(root, cls._meta.model)

    @classmethod
    def get_query(cls, info):
        def _build_match(info):
            pass

        def _build_projection(info):
            pass

        _match = _build_match(info)
        _projection = _build_projection(info)
        return cls._meta.queryset.find(_match, _projection)

    @classmethod
    def get_node(cls, info, id):
        return cls.get_query(info).get(id)

    @classmethod
    def postprocess_db_response(cls, document):
        return cls(**document)

    def resolve_id(self, info):
        # graphene_type = info.parent_type.graphene_type
        keys = self.__mapper__.primary_key_from_instance(self)
        return tuple(keys) if len(keys) > 1 else keys[0]
