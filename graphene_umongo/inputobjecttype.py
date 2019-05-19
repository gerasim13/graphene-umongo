import graphene
from graphql_relay.node.node import from_global_id

from .converter import (convert_model_to_attributes)


class InputObjectTypeOptions(graphene.types.inputobjecttype.InputObjectTypeOptions):
    model = None
    input_model_type = None
    embedded_inputs = None


class InputObjectType(graphene.InputObjectType):
    @classmethod
    def __init_subclass_with_meta__(cls, container=None, _meta=None, **options):
        def _iter_fields(attributes):
            for i in vars(attributes):
                f = getattr(attributes, i)
                if not isinstance(f, graphene.Field):
                    continue
                yield i, f

        def _embedded_input_type(field):
            if isinstance(field.type, graphene.List):
                data_type = field.type.of_type
            else:
                data_type = field.type.__class__

            if issubclass(data_type, graphene.InputObjectType):
                return data_type
            return None

        if not _meta:
            _meta = InputObjectTypeOptions(cls)

        schema = options.pop('schema', None)
        input_model_type = options.pop('model', None)
        embedded_inputs = {}
        model = None
        if schema:
            model = schema._meta.model
            connection_factory = schema._meta.connection_field_factory

            attributes = convert_model_to_attributes(
                model,
                connection_field_factory=connection_factory,
                input_attributes=True)

            for name, field in _iter_fields(attributes):
                embedded_type = _embedded_input_type(field)
                if embedded_type:
                    embedded_inputs[name] = embedded_type
                setattr(cls, name, field)

        _meta.embedded_inputs = embedded_inputs
        _meta.model = input_model_type or model
        assert _meta.embedded_inputs is not None
        assert _meta.model is not None

        super().__init_subclass_with_meta__(
            container=container,
            _meta=_meta,
            **options)

    def to_dictionary(self, session):
        """Method to convert Graphene inputs into dictionary"""
        dictionary = dict(self)
        try:
            for key, value in dictionary.items():
                # Convert GraphQL global id to database id
                if key[-2:] == 'id':
                    dictionary[key] = self.from_global_id(value)
                elif key in self._meta.embedded_inputs:
                    embedded_input = self._meta.embedded_inputs[key]
                    model_cls = embedded_input._meta.model
                    if isinstance(value, list):
                        dictionary[key] = [
                            self.to_embedded_model(session, model_cls, **v)
                            for v in value
                        ]
                    else:
                        dictionary[key] = self.to_embedded_model(
                            session, model_cls, **value)
        except Exception as e:
            session.rollback()
            raise e
        return dictionary

    @classmethod
    def from_global_id(self, global_id):
        try:
            return from_global_id(global_id)[1]
        except Exception as _:
            pass
        return global_id

    @classmethod
    def to_embedded_model(self, session, model_cls, **data):
        model = None
        model_id = self.from_global_id(data.get('id'))
        if model_id:
            model = session.query(model_cls).get(model_id)
            data['id'] = model_id

        if not model:
            model = model_cls(**data)
        else:
            for field, value in data.items():
                if getattr(model, field) == value:
                    continue
                setattr(model, field, value)
        return model
