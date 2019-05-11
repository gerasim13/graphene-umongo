class Registry(object):
    def __init__(self):
        self._registry_models = {}
        self._registry_embeds = {}
        self._registry_querysets = {}
        self._registry_composites = {}
        self._registry_unions = {}

    def register(self, cls):
        from .types import ObjectType

        assert issubclass(cls, ObjectType), f'Only classes of type ' \
            f'{ObjectType} can be registered, received "{cls.__name__}"'
        assert cls._meta.registry == self, 'Registry for a Model have to match.'
        self._registry_models[cls._meta.model] = cls

    def get_type_for_model(self, model):
        return self._registry_models.get(model)

    def register_embedded_model(self, model, cls):
        self._registry_embeds[model] = cls

    def get_embedded_model_type(self, model):
        return self._registry_embeds.get(model)

    def register_queryset(self, model, queryset):
        self._registry_querysets[model] = queryset

    def get_queryset(self, model):
        return self._registry_querysets.get(model)

    def register_composite_converter(self, composite, converter):
        self._registry_composites[composite] = converter

    def get_converter_for_composite(self, composite):
        return self._registry_composites.get(composite)

    def register_union(self, model, union):
        self._registry_unions[model] = union

    def get_union(self, model):
        return self._registry_unions.get(model)


registry = None


def get_global_registry():
    global registry
    if not registry:
        registry = Registry()
    return registry


def reset_global_registry():
    global registry
    registry = None
