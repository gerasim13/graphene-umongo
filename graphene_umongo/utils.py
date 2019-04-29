from umongo.abstract import BaseField


def iter_umongo_fields(model):
    fields = dir(model)
    for n in fields:
        f = getattr(model, n)
        if not f or not isinstance(f, BaseField):
            continue
        yield n, f
