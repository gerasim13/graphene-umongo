import graphene
from sqlalchemy.inspection import inspect


class MutationOptions(graphene.types.mutation.MutationOptions):
    session = None


class Mutation(graphene.Mutation):
    @classmethod
    def __init_subclass_with_meta__(cls,
                                    resolver=None,
                                    output=None,
                                    session=None,
                                    arguments=None,
                                    _meta=None,
                                    **options):
        if not _meta:
            _meta = MutationOptions(cls)
        _meta.session = session

        super().__init_subclass_with_meta__(
            resolver, output, arguments, _meta, **options)

    @classmethod
    def mutate(cls, root, info, input=None):
        db_session = cls._meta.session
        if callable(db_session):
            db_session = db_session(info)
        assert db_session, 'No db session provided'

        data = input.to_dictionary(db_session)
        output = cls._meta.output
        assert output, f'no output for {cls}'
        new_record = cls.upsert(
            info.context, output._meta.model, db_session, **data)
        return output(**new_record.as_dict())

    @classmethod
    def upsert(cls, context, model_cls, session, **data):
        model_pk = data.get(inspect(model_cls).primary_key[0].name)
        model = session.query(model_cls).get(model_pk) if model_pk else None

        try:
            if not model:
                model = model_cls(**data)
                session.add(model)
            else:
                for field, value in data.items():
                    if getattr(model, field) == value:
                        continue
                    setattr(model, field, value)
        except Exception as e:
            session.rollback()
            raise e
        else:
            session.commit()

        return model
