import functools
import umongo
import graphene


def get_column_doc(column):
    return getattr(column, "doc", None)


def is_column_nullable(column):
    return bool(getattr(column, "nullable", True))


def convert_umongo_field(f, registry=None):
    return convert_umongo_type(f, registry)


def convert_umongo_model(m, registry=None):
    return registry.get_type_for_model(m)


@functools.singledispatch
def convert_umongo_type(f, registry=None):
    raise Exception(f"Don't know how to convert the uMongo type {f} "
                    f"({f.__class__})")


@convert_umongo_type.register(umongo.fields.ObjectIdField)
@convert_umongo_type.register(umongo.fields.ReferenceField)
@convert_umongo_type.register(umongo.fields.GenericReferenceField)
def convert_id_field(f, registry=None):
    return graphene.ID(description=get_column_doc(f),
                       required=not (is_column_nullable(f)))


@convert_umongo_type.register(umongo.fields.UUIDField)
def convert_uuid_field(f, registry=None):
    return graphene.UUID(description=get_column_doc(f),
                         required=not (is_column_nullable(f)))


@convert_umongo_type.register(umongo.fields.StringField)
@convert_umongo_type.register(umongo.fields.StrField)
@convert_umongo_type.register(umongo.fields.FormattedStringField)
@convert_umongo_type.register(umongo.fields.UrlField)
@convert_umongo_type.register(umongo.fields.URLField)
@convert_umongo_type.register(umongo.fields.EmailField)
@convert_umongo_type.register(umongo.fields.ConstantField)
def convert_str_field(f, registry=None):
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
    _type = convert_umongo_model(f.embedded_document, registry)
    return graphene.Field(_type,
                          description=get_column_doc(f),
                          required=not (is_column_nullable(f)))


@convert_umongo_type.register(umongo.fields.ListField)
def convert_list_field(f, registry=None):
    _type = convert_umongo_model(f.container.embedded_document, registry)
    return graphene.List(_type,
                         description=get_column_doc(f),
                         required=not (is_column_nullable(f)))
