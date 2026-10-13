from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.main import app
from app.models.user import User


client = TestClient(app)


def register_user(prefix: str) -> tuple[dict, str]:
    email = f"{prefix}_{uuid4().hex[:10]}@example.com"
    password = "RootTraceTest123!"

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": f"{prefix} Test User",
        },
    )

    assert response.status_code == 201, response.text

    payload = response.json()

    assert payload["access_token"]
    assert payload["token_type"] == "bearer"
    assert payload["user"]["email"] == email

    return payload, email


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_team2_full_backend_flow():
    owner_payload = None
    member_payload = None
    project_id = None
    created_user_ids = []

    try:
        # ---------------------------------------------------------
        # 1. REGISTER OWNER
        # ---------------------------------------------------------
        owner_payload, owner_email = register_user("team2_owner")
        owner_token = owner_payload["access_token"]
        owner_id = owner_payload["user"]["id"]
        created_user_ids.append(owner_id)

        owner_headers = auth_headers(owner_token)

        # ---------------------------------------------------------
        # 2. VERIFY LOGIN
        # ---------------------------------------------------------
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": owner_email,
                "password": "RootTraceTest123!",
            },
        )

        assert login_response.status_code == 200
        login_payload = login_response.json()
        assert login_payload["user"]["id"] == owner_id

        # ---------------------------------------------------------
        # 3. VERIFY CURRENT USER
        # ---------------------------------------------------------
        me_response = client.get(
            "/api/v1/users/me",
            headers=owner_headers,
        )

        assert me_response.status_code == 200
        assert me_response.json()["id"] == owner_id

        # ---------------------------------------------------------
        # 4. REGISTER MEMBER
        # ---------------------------------------------------------
        member_payload, member_email = register_user("team2_member")
        member_token = member_payload["access_token"]
        member_id = member_payload["user"]["id"]
        created_user_ids.append(member_id)

        member_headers = auth_headers(member_token)

        # ---------------------------------------------------------
        # 5. CREATE PROJECT AS OWNER
        # ---------------------------------------------------------
        project_response = client.post(
            "/api/v1/projects",
            headers=owner_headers,
            json={
                "name": "Team 2 Integration Project",
                "description": "Temporary integration-test project",
            },
        )

        assert project_response.status_code == 201, project_response.text

        project = project_response.json()
        project_id = project["id"]

        assert project["owner_id"] == owner_id
        assert project["name"] == "Team 2 Integration Project"

        # ---------------------------------------------------------
        # 6. OWNER CAN VIEW PROJECT
        # ---------------------------------------------------------
        get_project_response = client.get(
            f"/api/v1/projects/{project_id}",
            headers=owner_headers,
        )

        assert get_project_response.status_code == 200
        assert get_project_response.json()["id"] == project_id

        # ---------------------------------------------------------
        # 7. MEMBER CANNOT ACCESS PROJECT YET
        # ---------------------------------------------------------
        before_membership = client.get(
            f"/api/v1/projects/{project_id}",
            headers=member_headers,
        )

        assert before_membership.status_code == 403

        # ---------------------------------------------------------
        # 8. OWNER ADDS MEMBER
        # ---------------------------------------------------------
        add_member_response = client.post(
            f"/api/v1/projects/{project_id}/members",
            headers=owner_headers,
            json={
                "email": member_email,
                "role": "member",
            },
        )

        assert add_member_response.status_code == 201, add_member_response.text

        membership = add_member_response.json()

        assert membership["user_id"] == member_id
        assert membership["project_id"] == project_id
        assert membership["role"] == "member"

        # ---------------------------------------------------------
        # 9. MEMBER CAN NOW VIEW PROJECT
        # ---------------------------------------------------------
        member_project_response = client.get(
            f"/api/v1/projects/{project_id}",
            headers=member_headers,
        )

        assert member_project_response.status_code == 200

        # ---------------------------------------------------------
        # 10. MEMBER CREATES TASK
        # ---------------------------------------------------------
        task_response = client.post(
            "/api/v1/tasks",
            headers=member_headers,
            json={
                "project_id": project_id,
                "title": "Investigate checkout failure",
                "description": "Integration test task",
                "status": "todo",
                "priority": "high",
                "assignee_id": member_id,
            },
        )

        assert task_response.status_code == 201, task_response.text

        task = task_response.json()
        task_id = task["id"]

        assert task["project_id"] == project_id
        assert task["title"] == "Investigate checkout failure"
        assert task["assignee_id"] == member_id

        # ---------------------------------------------------------
        # 11. MEMBER CAN READ TASK
        # ---------------------------------------------------------
        get_task_response = client.get(
            f"/api/v1/tasks/{task_id}",
            headers=member_headers,
        )

        assert get_task_response.status_code == 200
        assert get_task_response.json()["id"] == task_id

        # ---------------------------------------------------------
        # 12. MEMBER UPDATES TASK STATUS
        # ---------------------------------------------------------
        update_task_response = client.patch(
            f"/api/v1/tasks/{task_id}",
            headers=member_headers,
            json={
                "status": "in_progress",
            },
        )

        assert update_task_response.status_code == 200, update_task_response.text

        updated_task = update_task_response.json()

        assert updated_task["status"] == "in_progress"

        # ---------------------------------------------------------
        # 13. MEMBER ADDS COMMENT
        # ---------------------------------------------------------
        comment_response = client.post(
            f"/api/v1/tasks/{task_id}/comments",
            headers=member_headers,
            json={
                "content": "Investigating the database connection issue.",
            },
        )

        assert comment_response.status_code == 201, comment_response.text

        comment = comment_response.json()

        assert comment["task_id"] == task_id
        assert comment["user_id"] == member_id
        assert comment["content"] == (
            "Investigating the database connection issue."
        )

        # ---------------------------------------------------------
        # 14. READ COMMENTS
        # ---------------------------------------------------------
        comments_response = client.get(
            f"/api/v1/tasks/{task_id}/comments",
            headers=member_headers,
        )

        assert comments_response.status_code == 200

        comments = comments_response.json()

        assert any(
            item["id"] == comment["id"]
            for item in comments
        )

        # ---------------------------------------------------------
        # 15. VERIFY MEMBER NOTIFICATIONS
        # ---------------------------------------------------------
        notifications_response = client.get(
            "/api/v1/notifications",
            headers=member_headers,
        )

        assert notifications_response.status_code == 200

        notifications = notifications_response.json()

        notification_types = {
            item["notification_type"]
            for item in notifications
        }

        assert "project_membership" in notification_types

        # ---------------------------------------------------------
        # 16. VERIFY ACTIVITY LOG
        # ---------------------------------------------------------
        activity_response = client.get(
            f"/api/v1/projects/{project_id}/activity",
            headers=member_headers,
        )

        assert activity_response.status_code == 200

        activities = activity_response.json()

        activity_actions = {
            item["action"]
            for item in activities
        }

        assert "created" in activity_actions
        assert "updated" in activity_actions
        assert "member_added" in activity_actions

        # ---------------------------------------------------------
        # 17. OWNER CAN CHANGE MEMBER ROLE
        # ---------------------------------------------------------
        role_response = client.patch(
            f"/api/v1/projects/{project_id}/members/{member_id}",
            headers=owner_headers,
            json={
                "role": "admin",
            },
        )

        assert role_response.status_code == 200, role_response.text
        assert role_response.json()["role"] == "admin"

        # ---------------------------------------------------------
        # 18. MEMBER SEES ROLE-CHANGE NOTIFICATION
        # ---------------------------------------------------------
        notifications_after_role_change = client.get(
            "/api/v1/notifications",
            headers=member_headers,
        )

        assert notifications_after_role_change.status_code == 200

        role_notifications = notifications_after_role_change.json()

        assert any(
            item["notification_type"] == "role_changed"
            for item in role_notifications
        )

        # ---------------------------------------------------------
        # 19. MARK ONE NOTIFICATION READ
        # ---------------------------------------------------------
        unread_notifications = [
            item
            for item in role_notifications
            if not item["is_read"]
        ]

        if unread_notifications:
            notification_id = unread_notifications[0]["id"]

            read_response = client.patch(
                f"/api/v1/notifications/{notification_id}/read",
                headers=member_headers,
            )

            assert read_response.status_code == 200
            assert read_response.json()["is_read"] is True

        # ---------------------------------------------------------
        # 20. MARK ALL NOTIFICATIONS READ
        # ---------------------------------------------------------
        read_all_response = client.post(
            "/api/v1/notifications/read-all",
            headers=member_headers,
        )

        assert read_all_response.status_code == 200
        assert "updated" in read_all_response.json()

        # ---------------------------------------------------------
        # 21. VERIFY RBAC: MEMBER CANNOT DELETE TASK
        # ---------------------------------------------------------
        # Member was promoted to admin above, so admin SHOULD now
        # be allowed to delete it. This also verifies role change
        # affects authorization immediately.
        delete_task_response = client.delete(
            f"/api/v1/tasks/{task_id}",
            headers=member_headers,
        )

        assert delete_task_response.status_code == 204

        # ---------------------------------------------------------
        # 22. VERIFY TASK IS GONE
        # ---------------------------------------------------------
        deleted_task_response = client.get(
            f"/api/v1/tasks/{task_id}",
            headers=member_headers,
        )

        assert deleted_task_response.status_code == 404

    finally:
        # ---------------------------------------------------------
        # CLEANUP
        # ---------------------------------------------------------
        db = SessionLocal()

        try:
            if project_id is not None:
                project_response = client.get(
                    f"/api/v1/projects/{project_id}",
                    headers=auth_headers(
                        owner_payload["access_token"]
                    ) if owner_payload else {},
                )

                if project_response.status_code == 200:
                    client.delete(
                        f"/api/v1/projects/{project_id}",
                        headers=auth_headers(
                            owner_payload["access_token"]
                        ),
                    )

            # Delete test users directly.
            for user_id in created_user_ids:
                user = db.get(User, user_id)

                if user is not None:
                    db.delete(user)

            db.commit()

        finally:
            db.close()
