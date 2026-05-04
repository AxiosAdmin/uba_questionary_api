"""
Este módulo define as permissões para diferentes papéis de usuário na aplicação.

O dicionário PERMISSIONS mapeia nomes de papéis para suas ações permitidas em vários recursos,
como perguntas e perfis.
"""

PERMISSIONS = {
    "basic_uba_user": {
        "questions": ["GET"],
        "ai": ["POST"],
    }
}
