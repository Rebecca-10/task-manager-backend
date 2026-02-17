
from flask import Blueprint, jsonify, request, g
from db_helpers import get_db_connection
import psycopg2, psycopg2.extras
from auth_middleware import token_required

tasks_blueprint = Blueprint('tasks_blueprint', __name__)

@tasks_blueprint.route("/tasks", methods=["GET"])
@token_required
def tasks_index():
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Retrieve tasks for the current user
        cursor.execute("""
            SELECT t.id, t.user_id, t.title, t.description, t.priority, t.due_date, t.completed
            FROM tasks t
            WHERE t.user_id = %s
            ORDER BY t.id;
        """, (g.user["id"],))

        tasks = cursor.fetchall()
        consolidated_tasks = consolidate_tasks(tasks)

        connection.commit()
        connection.close()
        return jsonify({"tasks": consolidated_tasks}), 200

    except Exception as error:
        return jsonify({"error": str(error)}), 500

@tasks_blueprint.route('/tasks', methods=['POST'])
@token_required
def create_task():
    
    try:
        new_task = request.json
        new_task["user_id"] = g.user["id"]  
        connection = get_db_connection()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cursor.execute("""
            INSERT INTO tasks (user_id, title, description, priority, due_date, completed)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING *;
        """, (
            new_task["user_id"],
            new_task["title"],
            new_task.get("description"),
            new_task.get("priority"),
            new_task.get("due_date"),   
            new_task.get("completed", False)
        ))

        created_task = cursor.fetchone()
        connection.commit()
        connection.close()

        return jsonify({"task": created_task}), 201

    except Exception as error:
        return jsonify({"error": str(error)}), 500

@tasks_blueprint.route('/tasks/<int:task_id>', methods=['GET'])
@token_required
def show_task(task_id):
    """
    Return a single task for the logged-in user.
    """
    try:
        connection = get_db_connection()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cursor.execute("""
            SELECT t.id, t.user_id, t.title, t.description, t.priority, t.due_date, t.completed
            FROM tasks t
            WHERE t.id = %s AND t.user_id = %s;
        """, (task_id, g.user["id"]))

        task = cursor.fetchone()
        connection.close()

        if task:
            return jsonify({"task": task}), 200
        else:
            return jsonify({"error": "Task not found"}), 404

    except Exception as error:
        return jsonify({"error": str(error)}), 500

@tasks_blueprint.route('/tasks/<task_id>', methods=['PUT'])
@token_required
def update_task(task_id):
    try:
        updated_task_data = request.json
        connection = get_db_connection()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

       
        cursor.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
        task_to_update = cursor.fetchone()
        if task_to_update is None:
            return jsonify({"error": "Task not found"}), 404

        connection.commit()

       
        if task_to_update["user_id"] != g.user["id"]:
            return jsonify({"error": "Unauthorized"}), 401

        # Update the task
        cursor.execute("""
            UPDATE tasks
            SET title = %s, description = %s, priority = %s, due_date = %s, completed = %s
            WHERE id = %s
            RETURNING *;
        """, (
            updated_task_data["title"],
            updated_task_data["description"],
            updated_task_data["priority"],
            updated_task_data["due_date"],
            updated_task_data["completed"],
            task_id
        ))

        updated_task = cursor.fetchone()
        connection.commit()
        connection.close()

        return jsonify({"task": updated_task}), 200

    except Exception as error:
        return jsonify({"error": str(error)}), 500


@tasks_blueprint.route('/tasks/<task_id>', methods=['DELETE'])
@token_required
def delete_task(task_id):
    try:
        connection = get_db_connection()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        
        cursor.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
        task_to_delete = cursor.fetchone()
        if task_to_delete is None:
            return jsonify({"error": "Task not found"}), 404

        connection.commit()

        if task_to_delete["user_id"] != g.user["id"]:
            return jsonify({"error": "Unauthorized"}), 401

        cursor.execute("DELETE FROM tasks WHERE id = %s RETURNING *", (task_id,))
        deleted_task = cursor.fetchone()
        connection.commit()
        connection.close()

        return jsonify({"task": deleted_task}), 200

    except Exception as error:
        return jsonify({"error": str(error)}), 500
