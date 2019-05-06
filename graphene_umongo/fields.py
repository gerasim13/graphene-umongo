from functools import partial

import graphene
from graphene.relay import Connection
from graphene.relay.connection import PageInfo
from graphql_relay.connection.arrayconnection import connection_from_list_slice
from promise import Promise, is_thenable

from .registry import get_global_registry
from .utils import get_query


class UnsortedConnectionField(graphene.relay.ConnectionField):
    @property
    def type(self):
        from .types import ObjectType

        _type = super(graphene.relay.ConnectionField, self).type
        if issubclass(_type, Connection):
            return _type
        assert issubclass(_type, ObjectType),\
            f'{self.__class__.__name__} ' \
            f'only accepts {ObjectType.__name__} types, ' \
            f'not {_type.__name__}'
        assert _type._meta.connection,\
            f'The type {_type.__name__} doesn\'t have a connection'
        return _type._meta.connection

    @property
    def model(self):
        return self.type._meta.node._meta.model

    @classmethod
    async def get_query(cls, model, info, sort=None, **args):
        reg = get_global_registry()
        queryset = reg.get_queryset(model)
        query = await get_query(model, queryset.find, info)
        if sort is not None:
            if isinstance(sort, str):
                query = query.order_by(sort.value)
            else:
                query = query.order_by(*(col.value for col in sort))
        return query

    @classmethod
    async def resolve_connection(cls, connection_type, model, info, args,
                                 resolved):
        if resolved is None:
            resolved = await cls.get_query(model, info, **args)

        _len = len(resolved)
        connection = connection_from_list_slice(resolved, args, slice_start=0,
                                                list_length=_len,
                                                list_slice_length=_len,
                                                connection_type=connection_type,
                                                pageinfo_type=PageInfo,
                                                edge_type=connection_type.Edge)
        connection.iterable = resolved
        connection.length = _len
        return connection

    @classmethod
    def connection_resolver(cls, resolver, connection_type, model, root, info,
                            **args):
        resolved = resolver(root, info, **args)
        on_resolve = partial(cls.resolve_connection, connection_type, model,
                             info, args)
        if is_thenable(resolved):
            return Promise.resolve(resolved).then(on_resolve)

        return on_resolve(resolved)

    def get_resolver(self, parent_resolver):
        return partial(self.connection_resolver,
                       parent_resolver,
                       self.type,
                       self.model)


class ConnectionField(UnsortedConnectionField):
    def __init__(self, type, *args, **kwargs):
        if "sort" not in kwargs and issubclass(type, Connection):
            # Let super class raise if type is not a Connection
            try:
                model = type.Edge.node._type._meta.model
                kwargs.setdefault("sort", sort_argument_for_model(model))
            except Exception:
                raise Exception(
                    'Cannot create sort argument for {}. A model is required. '
                    'Set the "sort" argument to None to disabling the '
                    'creation of the sort query argument'.format(
                        type.__name__))
        elif "sort" in kwargs and kwargs["sort"] is None:
            del kwargs["sort"]
        super().__init__(type, *args, **kwargs)


def default_connection_field_factory(relationship, registry):
    model = relationship.mapper.entity
    model_type = registry.get_type_for_model(model)
    return model_type.Meta.connection_field_factory(model_type)
