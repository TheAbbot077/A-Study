from django.urls import path

from apps.ariel.api import views


app_name = "ariel"

urlpatterns = [
    # Identity lifecycle
    path("identities/", views.create_ariel_identity, name="create_identity"),
    path("identities/<uuid:identity_id>/", views.get_ariel_identity, name="get_identity"),
    path("identities/<uuid:identity_id>/activate/", views.activate_ariel, name="activate_ariel"),
    path("identities/<uuid:identity_id>/suspend/", views.suspend_ariel, name="suspend_ariel"),
    path("identities/<uuid:identity_id>/reset/", views.reset_ariel, name="reset_ariel"),
    # Teaching sessions
    path("identities/<uuid:identity_id>/sessions/", views.list_teaching_sessions, name="list_sessions"),
    path("identities/<uuid:identity_id>/sessions/start/", views.start_teaching_session, name="start_session"),
    # Teaching turns
    path("sessions/<uuid:session_id>/turns/", views.list_teaching_turns, name="list_turns"),
    path("sessions/<uuid:session_id>/turns/add/", views.add_teaching_turn, name="add_turn"),
    # Teach-back
    path("teach-back/strategies/", views.list_teach_back_strategies, name="list_teach_back_strategies"),
    path("sessions/<uuid:session_id>/teach-back/", views.start_teach_back, name="start_teach_back"),
    path("sessions/<uuid:session_id>/teach-back/<uuid:interaction_id>/", views.get_teach_back_interaction, name="get_teach_back_interaction"),
    path("sessions/<uuid:session_id>/teach-back/<uuid:interaction_id>/present/", views.present_teach_back_interaction, name="present_teach_back_interaction"),
    path("sessions/<uuid:session_id>/teach-back/<uuid:interaction_id>/respond/", views.respond_teach_back_interaction, name="respond_teach_back_interaction"),
    path("sessions/<uuid:session_id>/teach-back/<uuid:interaction_id>/artefact/", views.request_teach_back_artefact, name="request_teach_back_artefact"),
    path("sessions/<uuid:session_id>/teach-back/<uuid:interaction_id>/misunderstanding/", views.get_teach_back_misunderstanding, name="get_teach_back_misunderstanding"),
    path("sessions/<uuid:session_id>/teach-back/<uuid:interaction_id>/correct/", views.correct_teach_back_misunderstanding, name="correct_teach_back_misunderstanding"),
    path("sessions/<uuid:session_id>/teach-back/<uuid:interaction_id>/reteach/", views.request_delayed_reteach, name="request_delayed_reteach"),
    path("sessions/<uuid:session_id>/teach-back/from-artefact/", views.teach_back_from_artefact, name="teach_back_from_artefact"),
    path("sessions/<uuid:session_id>/teach-back/<uuid:interaction_id>/skip/", views.skip_teach_back_interaction, name="skip_teach_back_interaction"),
    path("sessions/<uuid:session_id>/teach-back/<uuid:interaction_id>/cancel/", views.cancel_teach_back_interaction, name="cancel_teach_back_interaction"),
    # Knowledge
    path("sessions/<uuid:session_id>/knowledge/create/", views.create_knowledge, name="create_knowledge"),
    path("identities/<uuid:identity_id>/knowledge/", views.list_knowledge, name="list_knowledge"),
    path("knowledge/<uuid:knowledge_id>/reinforce/", views.reinforce_knowledge, name="reinforce_knowledge"),
    path("knowledge/<uuid:knowledge_id>/correct/", views.correct_knowledge, name="correct_knowledge"),
    path("knowledge/<uuid:knowledge_id>/forget/", views.forget_knowledge, name="forget_knowledge"),
    path("knowledge/<uuid:knowledge_id>/retract/", views.retract_knowledge, name="retract_knowledge"),
    # Memory records & export
    path("identities/<uuid:identity_id>/memory-records/", views.list_memory_records, name="list_memory_records"),
    path("identities/<uuid:identity_id>/export/", views.export_memory, name="export_memory"),
]
