import server
from aiohttp import web
import aiohttp
import requests
import folder_paths
import os
import sys
import threading
import subprocess  # don't remove this
from urllib.parse import urlparse
import subprocess
import os
import json
from .version_control import update_version_if_outdated

WEB_DIRECTORY = "dist/entry"
NODE_CLASS_MAPPINGS = {}
__all__ = ['NODE_CLASS_MAPPINGS']
version = "V1.0.0"

print(f"### Loading: Workspace Manager ({version})")
workspace_path = os.path.join(os.path.dirname(__file__))
comfy_path = os.path.dirname(folder_paths.__file__)
db_dir_path = os.path.join(workspace_path, "db")


workspace_app = web.Application()
workspace_app.add_routes([
    web.static("/", os.path.join(workspace_path, 'dist/workspace')),
])
server.PromptServer.instance.app.add_subapp("/extensions/workspace/", workspace_app)

@server.PromptServer.instance.routes.post("/workspace/save_db")
async def save_db(request):
    # Extract parameters from the request
    data = await request.json()
    table = data['table']
    json_data = data['json']

    file_name = f'{db_dir_path}/{table}.json'
    if not os.path.exists(db_dir_path):
        os.makedirs(db_dir_path)

    # Write the JSON data to the specified file
    with open(file_name, 'w') as file:
        file.write(json.dumps(json_data, indent=4))

    return web.Response(text=f"JSON saved to {file_name}")


def read_table(table):
    if not table:
        return None
    file_name = f'{db_dir_path}/{table}.json'
    if not os.path.exists(file_name):
        return None

    with open(file_name, 'r') as file:
        data = json.load(file)
    return data


@server.PromptServer.instance.routes.get("/workspace/get_db")
async def get_workspace(request):
    # Extract the table parameter from the query string
    table = request.query.get('table')
    data = read_table(table)
    return web.json_response(data)

BACKUP_DIR = os.path.join(workspace_path, "backup")
MAX_BACKUP_FILES = 20


@server.PromptServer.instance.routes.post("/workspace/save_backup")
async def save_backup(request):
    try:
        data = await request.json()
        file_path = data.get('file_path')
        json_str = data.get('json_str')

        file_path = os.path.join(BACKUP_DIR, file_path)
        if not file_path or not json_str:
            return web.Response(text=json.dumps({"error": "file_path and json_str are required"}), status=400)
        directory = os.path.dirname(file_path)
        # Create the directory if it does not exist
        os.makedirs(directory, exist_ok=True)

        with open(file_path, 'w') as file:
            file.write(json_str)

        # Check the number of files in the directory after writing the new file
        files = [f for f in os.listdir(directory) if os.path.isfile(
            os.path.join(directory, f))]
        if len(files) > MAX_BACKUP_FILES:
            # Find the oldest file (smallest filename)
            oldest_file = min(files, key=lambda x: x)
            # Delete the oldest file
            os.remove(os.path.join(directory, oldest_file))

        return web.Response(text=json.dumps({"message": "File saved successfully"}), status=200)
    except Exception as e:
        return web.Response(text=json.dumps({"error": str(e)}), status=500)


@server.PromptServer.instance.routes.post("/workspace/list_backup")
async def list_backup(request):
    try:
        data = await request.json()
        dir_path = os.path.join(BACKUP_DIR, data.get('dir'))
        # List all files in the directory
        files = os.listdir(dir_path)

        # Filter out .json files and sort them by filename (which starts with Unix timestamp)
        json_files = sorted(
            [file for file in files if file.endswith('.json')],
            key=lambda x: x,  # Assuming the format is 'timestamp_filename.json'
            reverse=True
        )

        # Select the 10 most recent files
        recent_json_files = json_files[:10]

        # Read the contents of each JSON file
        file_contents = []
        for file in recent_json_files:
            with open(os.path.join(dir_path, file), 'r') as f:
                content = json.load(f)
                file_contents.append({"fileName": file, "jsonStr": content})

        return web.Response(text=json.dumps(file_contents), content_type='application/json')
    except Exception as e:
        return web.Response(text=json.dumps({"error": str(e)}), status=500)


@server.PromptServer.instance.routes.post("/workspace/get_system_dir")
async def get_system_dir(request):
    try:
        reqData = await request.json()
        dir_path = reqData['absolute_dir']
        if not dir_path:
            dir_path = comfy_path
        if not os.path.isdir(dir_path):
            raise ValueError("[workspace] get_system_dir Not a directory")

        dir_contents = [folder for folder in os.listdir(dir_path)
                        if os.path.isdir(os.path.join(dir_path, folder)) and not folder.startswith('.')]

        return web.Response(text=json.dumps({"dir_path": dir_path, "dir_contents": dir_contents}), content_type='application/json')
    except Exception as e:
        return web.Response(text=json.dumps({"error": str(e)}), status=500)


def get_my_workflows_dir():
    data = read_table('userSettings')
    if (data):
        records = json.loads(data)
        curDir = records['myWorkflowsDir'] if records else None
        if curDir:
            return curDir
    return os.path.join(comfy_path, 'my_workflows')


@server.PromptServer.instance.routes.post("/workspace/update_file")
async def update_file(request):
    data = await request.json()
    file_path = data['file_path']
    json_str = data['json_str']
    my_workflows_dir = get_my_workflows_dir()
    full_path = os.path.join(my_workflows_dir, file_path)
    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    with open(full_path, 'w', encoding='utf-8') as file:
        file.write(json_str)
    return web.Response(text="File updated successfully")


@server.PromptServer.instance.routes.post("/workspace/delete_file")
async def delete_file(request):
    data = await request.json()
    file_path = data['file_path']
    delete_empty_folder = data['deleteEmptyFolder']
    my_workflows_dir = get_my_workflows_dir()
    full_path = os.path.join(my_workflows_dir, file_path)

    if os.path.exists(full_path):
        os.remove(full_path)

        # Check if the directory is empty after deleting the file
        directory = os.path.dirname(full_path)
        if delete_empty_folder and not os.listdir(directory):
            # If the directory is empty, remove the directory
            os.rmdir(directory)
            return web.Response(text="File and empty directory deleted successfully")
        else:
            return web.Response(text="File deleted successfully")
    else:
        return web.Response(text="File not found", status=404)


@server.PromptServer.instance.routes.post("/workspace/rename_file")
async def rename_file(request):
    data = await request.json()
    file_path = data['file_path']
    new_name = data['new_file_path']

    if os.path.exists(file_path):
        os.rename(file_path, new_name)
        return web.Response(text="File renamed successfully")
    else:
        return web.Response(text="File not found", status=404)

image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
video_extensions = ['.mp4', '.mov', '.avi', '.webm', '.mkv']
@server.PromptServer.instance.routes.get("/workspace/view_media")
async def api_view_file(request):
    filename = request.query.get("filename", None)
    if not filename:
        return web.Response(status=404)

    output_path = folder_paths.get_output_directory()
    file_path = os.path.join(output_path, filename)

    if not os.path.exists(file_path):
        return web.Response(status=200)

    with open(file_path, 'rb') as f:
        media_file = f.read()

    content_type = 'application/json'
    file_extension = os.path.splitext(filename)[1].lower()
    if file_extension in image_extensions:
        content_type = f'image/{file_extension[1:]}'
    if file_extension in video_extensions:
        content_type = f'video/{file_extension[1:]}'

    return web.Response(
        body=media_file,
        content_type=content_type,
        headers={"Content-Disposition": f"filename=\"{filename}\""}
    )


@server.PromptServer.instance.routes.post("/workspace/open_workflow_file_browser")
async def open_workflow_file_browser(request):
    my_workflows_dir = get_my_workflows_dir()
    try:
        if sys.platform == 'win32':
            subprocess.run(['explorer', my_workflows_dir])
        elif sys.platform == 'darwin':
            subprocess.run(['open', my_workflows_dir])
        else:  # Assuming Unix/Linux
            subprocess.run(['xdg-open', my_workflows_dir])
        return web.Response(text=json.dumps('open successfully'), content_type='application/json')
    except Exception as e:
        return web.Response(text=json.dumps({"error": str(e)}), status=500)