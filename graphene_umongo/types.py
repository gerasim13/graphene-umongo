import graphene
import umongo
from graphene.types.utils import yank_fields_from_attrs

from .converter import construct_fields
from .querysets import BaseQueryset, FindQueryset, init_queryset
from .registry import Registry, get_global_registry
from .utils import get_query


class ObjectTypeOptions(graphene.types.objecttype.ObjectTypeOptions):
    model = None
    registry = None
    connection = None
    id = None


class ObjectType(graphene.types.objecttype.ObjectType):
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
        assert issubclass(model, umongo.document.DocumentImplementation),\
            f'You need to pass a valid uMongo Model in "{cls.__name__}", ' \
            f'received "{model}", {model.__bases__}'

        if not registry:
            registry = get_global_registry()
        assert isinstance(registry, Registry), f'The attribute registry in ' \
            f'{cls.__name__} needs to be an instance of Registry, received ' \
            f'\'{registry}\'.'

        if not queryset:
            queryset = FindQueryset
        assert issubclass(queryset, BaseQueryset), f'You need to pass ' \
            f'a valid queryset class, subclass of {BaseQueryset}, ' \
            f'received \'{queryset}\''
        queryset = init_queryset(queryset, model, cls)
        registry.register_queryset(model, queryset)
        assert registry.get_queryset(model) == queryset

        _fields = yank_fields_from_attrs(
            construct_fields(model.opts.template,
                             registry,
                             only_fields,
                            exclude_fields),
            _as=graphene.Field
        )

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
        _meta.id = id or "id"

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
        model = cls._meta.model
        return cls(**{
            model._from_mongo_world(k): v for k,v in document.items()
        })

        # model_template = model.opts.template.__dict__
        #
        # def _to_mongo_world(field_name):
        #     field = model_template.get(field_name)
        #     if field:
        #         return field.attribute or \
        #                getattr(field, 'marshmallow_attribute')
        #     return field_name
        #
        #
        # if '_id' in document:
        #     document['id'] = document['_id']
        #     del document['_id']
        # return cls(**document)

    # async def resolve_id(self, info):
    #     return self.id
