import functools
from collections import OrderedDict

import graphene
import umongo
from graphene.types.utils import yank_fields_from_attrs

from .registry import Registry, get_global_registry
from .utils import (iter_fields, _iter_umongo_model_offspring, get_column_doc,
                    is_column_required)


def construct_fields(m, registry,
                     only_fields=None,
                     exclude_fields=None,
                     input_attributes=False):
    fields = OrderedDict()
    for name, field_name, field in iter_fields(m, only_fields, exclude_fields):
        converted_field = convert_umongo_field(
            field, registry, input_attributes)
        if not converted_field:
            continue
        elif isinstance(converted_field, list):
            for f in converted_field:
                fields[f.name.lower()] = f
        else:
            fields[name] = converted_field
    return fields


def convert_umongo_field(f,
                         registry=None,
                         input_attributes=False):
    return convert_umongo_type(f, registry, input_attributes)


def convert_umongo_model(m,
                         registry=None,
                         input_attributes=False,
                         default_resolver=None):
    if input_attributes:
        _classname = f'{m.__name__}Input'
        _baseclass = graphene.InputObjectType
    else:
        _classname = m.__name__
        _baseclass = graphene.ObjectType

    _schema_cls = registry.get_embedded_model_type(_classname)
    if not _schema_cls:
        _fields = yank_fields_from_attrs(
            construct_fields(m, registry, input_attributes=input_attributes),
            _as=graphene.Field
        )
        if default_resolver and not input_attributes:
            _fields['Meta'] = type('Meta', (), {
                'default_resolver': default_resolver
            })
        _schema_cls = type(_classname, (_baseclass,), _fields)
        registry.register_embedded_model(_classname, _schema_cls)
    return _schema_cls


def get_attributes_fields(
        models,
        registry=None,
        input_attributes=False):
    _fields = yank_fields_from_attrs(construct_fields(
        models,
        registry,
        input_attributes=input_attributes
    ), _as=graphene.Field)
    return _fields


def convert_model_to_attributes(m,
                                f=None,
                                registry=None,
                                input_attributes=False):
    if not registry:
        registry = get_global_registry()
    assert isinstance(registry, Registry), f'The attribute registry in ' \
        f'{registry.__class__.__name__} needs to be an instance of Registry, '\
        f'received {registry}.'

    if input_attributes:
        _cls_name = m.__name__ + 'InputAttribute'
    else:
        _cls_name = m.__name__ + 'Attribute'

    attributes = registry.get_attributes_for_model(_cls_name)
    if not attributes:
        _fields = get_attributes_fields(
            m, registry,
            input_attributes=input_attributes)
        attributes = type(_cls_name, (object,), _fields)
        registry.register_attributes(attributes)
    return attributes


def convert_id_field(f,
                     registry=None,
                     input_attributes=False):
    return graphene.ID(description=get_column_doc(f),
                       required=not (is_column_required(f, input_attributes)))


@functools.singledispatch
def convert_umongo_type(f,
                        registry=None,
                        input_attributes=False):
    raise Exception(f"Don't know how to convert the uMongo type {f} "
                    f"({f.__class__}), "
                    f"convert_umongo_type: {convert_umongo_type.__dict__}")


@convert_umongo_type.register(umongo.fields.UUIDField)
def convert_uuid_field(f,
                       registry=None,
                       input_attributes=False):
    if f.attribute == '_id':
        return convert_id_field(f, registry)
    return graphene.UUID(
        description=get_column_doc(f),
        required=not (is_column_required(f, input_attributes)))


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
def convert_str_field(f,
                      registry=None,
                      input_attributes=False):
    if f.attribute == '_id':
        return convert_id_field(f, registry)
    return graphene.String(
        description=get_column_doc(f),
        required=not (is_column_required(f, input_attributes)))


@convert_umongo_type.register(umongo.fields.BooleanField)
@convert_umongo_type.register(umongo.fields.BoolField)
def convert_bool_field(f,
                       registry=None,
                       input_attributes=False):
    return graphene.Boolean(
        description=get_column_doc(f),
        required=not (is_column_required(f, input_attributes)))


@convert_umongo_type.register(umongo.fields.NumberField)
@convert_umongo_type.register(umongo.fields.IntegerField)
@convert_umongo_type.register(umongo.fields.IntField)
def convert_int_field(f,
                      registry=None,
                      input_attributes=False):
    return graphene.Int(
        description=get_column_doc(f),
        required=not (is_column_required(f, input_attributes)))


@convert_umongo_type.register(umongo.fields.FloatField)
@convert_umongo_type.register(umongo.fields.DecimalField)
def convert_float_field(f,
                        registry=None,
                        input_attributes=False):
    return graphene.Float(
        description=get_column_doc(f),
        required=not (is_column_required(f, input_attributes)))


@convert_umongo_type.register(umongo.fields.DateTimeField)
@convert_umongo_type.register(umongo.fields.StrictDateTimeField)
def convert_datetime_field(f,
                           registry=None,
                           input_attributes=False):
    return graphene.DateTime(
        description=get_column_doc(f),
        required=not (is_column_required(f, input_attributes)))


@convert_umongo_type.register(umongo.fields.DateField)
def convert_date_field(f,
                       registry=None,
                       input_attributes=False):
    return graphene.Date(
        description=get_column_doc(f),
        required=not (is_column_required(f, input_attributes)))


@convert_umongo_type.register(umongo.fields.DictField)
def convert_dict_field(f,
                       registry=None,
                       input_attributes=False):
    return graphene.Dynamic(
        description=get_column_doc(f),
        required=not (is_column_required(f, input_attributes)))


@convert_umongo_type.register(umongo.fields.EmbeddedField)
def convert_embedded_doc_field(f,
                               registry=None,
                               input_attributes=False):
    def _get_output_union_type(m, class_name):
        t = registry.get_union(class_name)
        if not t:
            types = [convert_umongo_model(o, registry, input_attributes)
                     for o in _iter_umongo_model_offspring(m)]
            fields = {'Meta': type('Meta', (), {'types': types})}
            t = type(class_name, (graphene.Union,), fields)
            registry.register_union(class_name, t)
        return t

    def _get_input_union_type(m):
        _types = list()
        for o in _iter_umongo_model_offspring(m):
            class_name = f'{o.__name__}Input'
            t = registry.get_union(class_name)
            if not t:
                fields = yank_fields_from_attrs(construct_fields(
                    o, registry, input_attributes=input_attributes),
                    _as=graphene.Field)
                t = type(class_name, (graphene.InputObjectType,), fields)
                registry.register_union(class_name, t)
            _types.append(t)
        return _types

    model = f.embedded_document
    is_abstract = getattr(model.Meta, 'abstract', False)
    if is_abstract and input_attributes:
        return [
            graphene.Field(t,
                           name=t.__name__.replace('Input', '').lower(),
                           description=get_column_doc(f),
                           required=False)
            for t in _get_input_union_type(model)
        ]
    elif is_abstract and not input_attributes:
        _type = _get_output_union_type(model, model.__name__)
    elif issubclass(type(model), umongo.template.MetaTemplate):
        _type = convert_umongo_model(
            model,
            registry,
            input_attributes,
            graphene.types.resolver.dict_resolver)
    else:
        _type = convert_umongo_type(
            model,
            registry,
            input_attributes)
    return graphene.Field(
        _type,
        description=get_column_doc(f),
        required=not (is_column_required(f, input_attributes)))


@convert_umongo_type.register(umongo.fields.ListField)
def convert_list_field(f,
                       registry=None,
                       input_attributes=False):
    if issubclass(type(f.container), umongo.template.MetaTemplate):
        _type = convert_umongo_model(
            f.container,
            registry,
            input_attributes,
            graphene.types.resolver.dict_resolver)
    else:
        _type = type(convert_umongo_type(
            f.container,
            registry,
            input_attributes))
    return graphene.List(
        _type,
        description=get_column_doc(f),
        required=not (is_column_required(f, input_attributes)))
