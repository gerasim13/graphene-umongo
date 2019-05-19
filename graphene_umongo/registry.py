class Registry(object):
    def __init__(self):
        self._registry_models = {}
        self._registry_embeds = {}
        self._registry_querysets = {}
        self._registry_attributes = {}
        self._registry_unions = {}

    def register(self, cls):
        from .types import ObjectType

        assert issubclass(cls, ObjectType), f'Only classes of type ' \
            f'{ObjectType} can be registered, received "{cls.__name__}"'
        assert cls._meta.registry == self, 'Registry for a Model have to match.'
        self._registry_models[cls._meta.model] = cls

    def get_type_for_model(self, model):
        return self._registry_models.get(model)

    def register_embedded_model(self, type_name, cls):
        self._registry_embeds[type_name] = cls

    def get_embedded_model_type(self, type_name):
        return self._registry_embeds.get(type_name)

    def register_queryset(self, model, queryset):
        self._registry_querysets[model] = queryset

    def get_queryset(self, model):
        return self._registry_querysets.get(model)

    def register_attributes(self, attributes_cls):
        self._registry_attributes[attributes_cls.__name__] = attributes_cls

    def get_attributes_for_model(self, attributes):
        return self._registry_attributes.get(attributes)

    def register_union(self, class_name, union):
        self._registry_unions[class_name] = union

    def get_union(self, class_name):
        return self._registry_unions.get(class_name)


registry = None


def get_global_registry():
    global registry
    if not registry:
        registry = Registry()
    return registry


def reset_global_registry():
    global registry
    registry = None
