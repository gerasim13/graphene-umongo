from umongo.abstract import BaseField


async def get_query(model, query_fn, info):
    # query = getattr(model, "query", None)
    # if not query:
    #     session = get_session(context)
    #     if not session:
    #         raise Exception(
    #             "A query in the model Base or a session in the schema is required for querying.\n"
    #             "Read more http://docs.graphene-python.org/projects/sqlalchemy/en/latest/tips/#querying")
    #     query = session.query(model)

    # def _to_mongo_world(field_name):
    #     field = model_template.get(field_name)
    #     if field:
    #         return field.attribute or getattr(field, 'marshmallow_attribute')
    #     return field_name

    def _iter_args(info):
        for field in info.field_asts:
            for arg in field.arguments:
                yield model._to_mongo_world(arg.name.value), arg.value.value

    def _build_match(args):
        return {k: v for k, v in args.items() if v}

    def _build_projection(args):
        return {k: True for k, v in args.items()}

    _args = {k: v for k, v in _iter_args(info)}
    _match = _build_match(_args)
    _projection = _build_projection(_args)
    return await query_fn(_match, _projection)


def iter_umongo_fields(model):
    fields = dir(model)
    for n in fields:
        f = getattr(model, n)
        if not f or not isinstance(f, BaseField):
            continue
        yield n, f
