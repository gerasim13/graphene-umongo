import functools
from collections import OrderedDict
import importlib

import graphene
import umongo
from graphene.types.utils import yank_fields_from_attrs

from .utils import iter_umongo_fields


def construct_fields(model, registry, only_fields=None, exclude_fields=None):
    fields = OrderedDict()
    for name, field in iter_umongo_fields(model):
        fields[name] = convert_umongo_field(field, registry)
    return fields


def get_column_doc(column):
    return column.metadata.get("doc", None)


def is_column_nullable(column):
    return not bool(getattr(column, "required", True)) \
           and bool(getattr(column, "allow_none", True))


def convert_umongo_field(f, registry=None):
    return convert_umongo_type(f, registry)


def convert_umongo_model(m, registry=None):
    _schema_cls = registry.get_embedded_model_type(m)
    if not _schema_cls:
        _fields = yank_fields_from_attrs(
            construct_fields(m, registry),
            _as=graphene.Field
        )
        _fields['Meta'] = type('Meta', (), {
            'default_resolver': graphene.types.resolver.dict_resolver
        })
        _schema_cls = type(m.__name__, (graphene.ObjectType,), _fields)
        registry.register_embedded_model(m, _schema_cls)
    return _schema_cls


def convert_id_field(f, registry=None):
    return graphene.ID(description=get_column_doc(f),
                       required=not (is_column_nullable(f)))


@functools.singledispatch
def convert_umongo_type(f, registry=None):
    raise Exception(f"Don't know how to convert the uMongo type {f} "
                    f"({f.__class__}), "
                    f"convert_umongo_type: {convert_umongo_type.__dict__}")


@convert_umongo_type.register(umongo.fields.UUIDField)
def convert_uuid_field(f, registry=None):
    if f.attribute == '_id':
        return convert_id_field(f, registry)
    return graphene.UUID(description=get_column_doc(f),
                         required=not (is_column_nullable(f)))


@convert_umongo_type.register(umongo.fields.ObjectIdField)
@convert_umongo_type.register(umongo.fields.ReferenceField)
@convert_umongo_type.register(umongo.fields.GenericReferenceField)
@convert_umongo_type.register(umongo.fields.StringField)
@convert_umongo_type.register(umongo.fields.StrField)
@convert_umongo_type.register(umongo.fields.FormattedStringField)
@convert_umongo_type.register(umongo.fields.UrlField)
@convert_umongo_type.register(umongo.fields.URLField)
@convert_umongo_type.register(umongo.fields.EmailField)
@convert_umongo_type.register(umongo.fields.ConstantField)
def convert_str_field(f, registry=None):
    if f.attribute == '_id':
        return convert_id_field(f, registry)
    return graphene.String(description=get_column_doc(f),
                           required=not (is_column_nullable(f)))


@convert_umongo_type.register(umongo.fields.BooleanField)
@convert_umongo_type.register(umongo.fields.BoolField)
def convert_bool_field(f, registry=None):
    return graphene.Boolean(description=get_column_doc(f),
                            required=not (is_column_nullable(f)))


@convert_umongo_type.register(umongo.fields.NumberField)
@convert_umongo_type.register(umongo.fields.IntegerField)
@convert_umongo_type.register(umongo.fields.IntField)
def convert_int_field(f, registry=None):
    return graphene.Int(description=get_column_doc(f),
                        required=not (is_column_nullable(f)))


@convert_umongo_type.register(umongo.fields.FloatField)
@convert_umongo_type.register(umongo.fields.DecimalField)
def convert_float_field(f, registry=None):
    return graphene.Float(description=get_column_doc(f),
                          required=not (is_column_nullable(f)))


@convert_umongo_type.register(umongo.fields.DateTimeField)
@convert_umongo_type.register(umongo.fields.StrictDateTimeField)
def convert_datetime_field(f, registry=None):
    return graphene.DateTime(description=get_column_doc(f),
                             required=not (is_column_nullable(f)))


@convert_umongo_type.register(umongo.fields.DateField)
def convert_date_field(f, registry=None):
    return graphene.Date(description=get_column_doc(f),
                         required=not (is_column_nullable(f)))


@convert_umongo_type.register(umongo.fields.DictField)
def convert_dict_field(f, registry=None):
    return graphene.Dynamic(description=get_column_doc(f),
                            required=not (is_column_nullable(f)))


@convert_umongo_type.register(umongo.fields.EmbeddedField)
def convert_embedded_doc_field(f, registry=None):
    model = f.embedded_document

    if getattr(model.Meta, 'abstract', False):
        module = importlib.import_module(model.__module__)
        model = getattr(module, model.__name__, model)

        _type = registry.get_union(model)
        if not _type:
            types = [
                convert_umongo_model(o, registry)
                for o in model.opts.offspring
            ]
            _type = type(
                model.__name__,
                (graphene.Union,),
                {'Meta': {'types': types}})
            registry.register_union(model, _type)
    elif issubclass(type(model), umongo.template.MetaTemplate):
        _type = convert_umongo_model(model, registry)
    else:
        _type = convert_umongo_type(model, registry)
    return graphene.Field(
        _type,
        description=get_column_doc(f),
        required=not (is_column_nullable(f)))


@convert_umongo_type.register(umongo.fields.ListField)
def convert_list_field(f, registry=None):
    if issubclass(type(f.container), umongo.template.MetaTemplate):
        _type = convert_umongo_model(f.container, registry)
    else:
        _type = type(convert_umongo_type(f.container, registry))
    return graphene.List(_type,
                         description=get_column_doc(f),
                         required=not (is_column_nullable(f)))
