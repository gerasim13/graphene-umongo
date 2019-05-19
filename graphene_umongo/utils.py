import importlib
from functools import lru_cache

from umongo.abstract import BaseField


def iter_fields(model,
                only_fields=(),
                exclude_fields=(),
                deep=False,
                parent_field=None):
    template = model.opts.template if hasattr(model, 'opts') else model
    fields = dir(template)

    def __(n, f, deep, parent_field):
        if not f or not isinstance(f, BaseField):
            return

        full_field_name = f'{parent_field}.{n}' if parent_field else n

        if deep:
            embedded_doc = _get_embedded_field_model_class(f)
            if embedded_doc:
                yield from _iter_umongo_embedded_fields(
                    embedded_doc, deep, full_field_name)
                return

        yield full_field_name, n, f

    for n in fields:
        f = getattr(template, n)
        if not isinstance(f, list):
            yield from __(n, f, deep, parent_field)
        else:
            for _f in f:
                yield from __(n, _f, deep, parent_field)


async def get_query(model, query_fn, info):
    python_fields = _get_umongo_python_world_fields(model)

    def _build_match(info):
        for field in info.field_asts:
            for arg in field.arguments:
                k = python_fields.get(arg.name.value)
                v = arg.value.value
                if not v:
                    continue
                yield k, v

    def _build_projection(match):
        for k, v in match.items():
            yield k, True

    _match = {k: v for k, v in _build_match(info)}
    _projection = {k: v for k, v in _build_projection(_match)}
    return await query_fn(_match, _projection)


def _iter_umongo_model_offspring(model_or_template):
    if hasattr(model_or_template, 'opts'):
        model = model_or_template
    else:
        module = importlib.import_module(model_or_template.__module__)
        model = getattr(module, model_or_template.__name__, model_or_template)

    for offspring in model.opts.offspring:
        yield offspring


def _iter_umongo_embedded_fields(embedded_model, deep=False, parent_field=None):
    if getattr(embedded_model.Meta, 'abstract', False):
        for o in _iter_umongo_model_offspring(embedded_model):
            yield from iter_fields(o, deep=deep, parent_field=parent_field)
    else:
        yield from iter_fields(
            embedded_model,
            deep=deep,
            parent_field=parent_field)


def _get_embedded_field_model_class(f):
    embedded_doc = None
    if hasattr(f, 'container') and hasattr(f.container, 'embedded_document'):
        embedded_doc = f.container.embedded_document
    elif hasattr(f, 'embedded_document'):
        embedded_doc = f.embedded_document
    return embedded_doc


@lru_cache(maxsize=None)
def _get_umongo_python_world_fields(model):
    _conv = {'id': '_id'}

    def _to_python_world(i, a):
        if a == '_id':
            return f"{'.'.join(i.split('.')[:-1])}.id"
        return i

    for i, n, f in iter_fields(model, deep=True):
        _conv[i] = _to_python_world(i, f.attribute)
    return _conv


@lru_cache(maxsize=None)
def _get_umongo_mongo_world_fields(model):
    _conv = {'_id': 'id'}

    def _to_mongo_world(i, a):
        if a == '_id':
            return f"{'.'.join(i.split('.')[:-1])}._id"
        return i

    for i, n, f in iter_fields(model, deep=True):
        _conv[_to_mongo_world(i, f.attribute)] = i
    return _conv


def get_column_doc(column):
    return column.metadata.get("doc", None)


def is_column_nullable(column):
    return not bool(getattr(column, "required", True)) \
           and bool(getattr(column, "allow_none", True))


def is_column_has_default(column):
    return bool(getattr(column, "default", None) is not None)


def is_column_required(column, for_input=False):
    if for_input:
        return not (is_column_has_default(column)
                    or is_column_nullable(column))
    return not is_column_nullable(column)
