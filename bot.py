import logging
import subprocess
import sys
import os
import re
import time
import concurrent.futures
import random
import discord
from discord.ext import commands, tasks
import docker
import asyncio
from discord import app_commands
import requests

# Set Your Bot Token gay
TOKEN = 'YOUR_BOT_TOKEN'
RAM_LIMIT = '2g' #Set Your Own Ram How Much You Want To Give Your Users
SERVER_LIMIT =#you can change it!
database_file = 'database.txt'

intents = discord.Intents.default()
intents.messages = False
intents.message_content = False

bot = commands.Bot(command_prefix='/', intents=intents)
client = docker.from_env()

whitelist_ids = {"1128161197766746213"}  # Replace with actual user IDs

# Utility Functions
def add_to_database(userid, container_name, ssh_command):
    with open(database_file, 'a') as f:
        f.write(f"{userid}|{container_name}|{ssh_command}\n")

def remove_from_database(ssh_command):
    if not os.path.exists(database_file):
        return
    with open(database_file, 'r') as f:
        lines = f.readlines()
    with open(database_file, 'w') as f:
        for line in lines:
            if ssh_command not in line:
                f.write(line)

def get_user_servers(user):
    if not os.path.exists(database_file):
        return []
    servers = []
    with open(database_file, 'r') as f:
        for line in f:
            if line.startswith(user):
                servers.append(line.strip())
    return servers

def count_user_servers(userid):
    return len(get_user_servers(userid))

def get_container_id_from_database(userid, container_name):
    if not os.path.exists(database_file):
        return None
    with open(database_file, 'r') as f:
        for line in f:
            if line.startswith(userid) and container_name in line:
                return line.split('|')[1]
    return None

def generate_random_port():
    return random.randint(1025, 65535)

async def capture_ssh_session_line(process):
    while True:
        output = await process.stdout.readline()
        if not output:
            break
        output = output.decode('utf-8').strip()
        if "ssh session:" in output:
            return output.split("ssh session:")[1].strip()
    return None



# In-memory database for user credits
user_credits = {}

# Cuty.io API key (Your account key)
API_KEY = 'ebe681f9e37ef61fcfd756396'


# Node Status Command
def get_node_status():
    try:
        containers = client.containers.list(all=True)
        container_status = "\n".join([f"{container.name} - {container.status}" for container in containers]) or "No containers running."

        # Get system-wide memory usage using `os` module
        with open('/proc/meminfo', 'r') as f:
            meminfo = f.read()
        mem_total = int(re.search(r'MemTotal:\s+(\d+)', meminfo).group(1)) / 1024  # Convert to MB
        mem_free = int(re.search(r'MemFree:\s+(\d+)', meminfo).group(1)) / 1024  # Convert to MB
        mem_available = int(re.search(r'MemAvailable:\s+(\d+)', meminfo).group(1)) / 1024  # Convert to MB

        memory_used = mem_total - mem_available
        memory_percentage = (memory_used / mem_total) * 100 if mem_total else 0

        node_info = {
            "containers": container_status,
            "memory_total": mem_total,
            "memory_used": memory_used,
            "memory_percentage": memory_percentage
        }
        return node_info
    except Exception as e:
        return str(e)

@bot.tree.command(name="node", description="Show the current status of the VPS node.")
async def node_status(interaction: discord.Interaction):
    try:
        node_info = get_node_status()

        if isinstance(node_info, str):  # If there's an error
            await interaction.response.send_message(embed=discord.Embed(description=f"### Error fetching node status: {node_info}", color=0xff0000))
            return

        # Format the status message
        embed = discord.Embed(title="VPS Node1 Status", color=0x00ff00)
        embed.add_field(name="Containers", value=node_info["containers"], inline=False)
        embed.add_field(name="Memory Usage", value=f"{node_info['memory_used']:.2f} / {node_info['memory_total']:.2f} MB ({node_info['memory_percentage']:.2f}%)", inline=False)

        await interaction.response.send_message(embed=embed)

    except Exception as e:
        await interaction.response.send_message(embed=discord.Embed(description=f"### Failed to fetch node status: {str(e)}", color=0xff0000))


# Remove Everything Task
async def remove_everything_task(interaction: discord.Interaction):
    await interaction.channel.send("### Node is full. Resetting all user instances...")
    try:
        subprocess.run("docker rm -f $(sudo docker ps -a -q)", shell=True, check=True)
        os.remove(database_file)
        subprocess.run("pkill pytho*", shell=True, check=True)
        await interaction.channel.send("### All instances and data have been reset.")
    except Exception as e:
        await interaction.channel.send(f"### Failed to reset instances: {str(e)}")

# KillVPS Command (Admin only)
@bot.tree.command(name="killvps", description="Kill all user VPS instances. Admin only.")
async def kill_vps(interaction: discord.Interaction):
    userid = str(interaction.user.id)
    if userid not in whitelist_ids:
        await interaction.response.send_message(embed=discord.Embed(description="You do not have permission to use this command.", color=0xff0000))
        return

    await remove_everything_task(interaction)
    await interaction.response.send_message(embed=discord.Embed(description="### All user VPS instances have been terminated.", color=0x00ff00))

def add_to_database(userid, container_name, ssh_command):
    with open(database_file, 'a') as f:
        f.write(f"{userid}|{container_name}|{ssh_command}\n")

def remove_from_database(ssh_command):
    if not os.path.exists(database_file):
        return
    with open(database_file, 'r') as f:
        lines = f.readlines()
    with open(database_file, 'w') as f:
        for line in lines:
            if ssh_command not in line:
                f.write(line)

async def capture_ssh_session_line(process):
    while True:
        output = await process.stdout.readline()
        if not output:
            break
        output = output.decode('utf-8').strip()
        if "ssh session:" in output:
            return output.split("ssh session:")[1].strip()
    return None

whitelist_ids = {"1128161197766746213"}  # Replace with actual user IDs

@bot.tree.command(name="remove-everything", description="Removes all data and containers")
async def remove_everything(interaction: discord.Interaction):
    userid = str(interaction.user.id)
    if userid not in whitelist_ids:
        await interaction.response.send_message(embed=discord.Embed(description="You do not have permission to use this command.", color=0xff0000))
        return

    # Remove all Docker containers
    try:
        subprocess.run("docker rm -f $(sudo docker ps -a -q)", shell=True, check=True)
        await interaction.response.send_message(embed=discord.Embed(description="All Docker containers have been removed.", color=0x00ff00))
    except subprocess.CalledProcessError as e:
        await interaction.response.send_message(embed=discord.Embed(description="Failed to remove Docker containers.", color=0xff0000))

    # Remove database and port files
    try:
        os.remove(database_file)
        os.remove(port_db_file)
        await interaction.response.send_message(embed=discord.Embed(description="Database and port files have been cleared. Service has been restarted. Please start the bot in the shell", color=0x00ff00))
        subprocess.run("pkill pytho*", shell=True, check=True)
    except Exception as e:
        await interaction.response.send_message(embed=discord.Embed(description=f"Failed to clear database or restart service: {str(e)}", color=0xff0000))

#@tasks.loop(seconds=5)
#async def change_status():
#    try:
#        if os.path.exists(database_file):
#            with open(database_file, 'r') as f:
#                lines = f.readlines()
#                instance_count = len(lines)
#        else:
#            instance_count = 0
#
#        status = f"with {instance_count} Cloud Instances"
#        await bot.change_presence(activity=discord.Game(name=status))
#    except Exception as e:
#        print(f"Failed to update status: {e}")

def get_ssh_command_from_database(container_id):
    if not os.path.exists(database_file):
        return None
    with open(database_file, 'r') as f:
        for line in f:
            if container_id in line:
                return line.split('|')[2]
    return None

def get_user_servers(user):
    if not os.path.exists(database_file):
        return []
    servers = []
    with open(database_file, 'r') as f:
        for line in f:
            if line.startswith(user):
                servers.append(line.strip())
    return servers

def count_user_servers(userid):
    return len(get_user_servers(userid))

def get_container_id_from_database(userid):
    servers = get_user_servers(userid)
    if servers:
        return servers[0].split('|')[1]
    return None

@bot.event
async def on_ready():
    #change_status.start()
    print(f'Bot is ready. Logged in as {bot.user}')
    await bot.tree.sync()

async def regen_ssh_command(interaction: discord.Interaction, container_name: str):
#    await interaction.response.defer()
    user = str(interaction.user)
    container_id = get_container_id_from_database(user, container_name)

    if not container_id:
        await interaction.response.send_message(embed=discord.Embed(description="### No active instance found for your user.", color=0xff0000))
        return

    try:
        exec_cmd = await asyncio.create_subprocess_exec("docker", "exec", container_id, "tmate", "-F",
                                                        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        await interaction.response.send_message(embed=discord.Embed(description=f"Error executing tmate in Docker container: {e}", color=0xff0000))
        return

    ssh_session_line = await capture_ssh_session_line(exec_cmd)
    if ssh_session_line:
        await interaction.user.send(embed=discord.Embed(description=f"### New SSH Session Command: ```{ssh_session_line}```", color=0x00ff00))
        await interaction.response.send_message(embed=discord.Embed(description="### New SSH session generated. Check your DMs for details.", color=0x00ff00))
    else:
        await interaction.response.send_message(embed=discord.Embed(description="### Failed to generate new SSH session.", color=0xff0000))

async def start_server(interaction: discord.Interaction, container_name: str):
#    await interaction.response.defer()
    userid = str(interaction.user.id)
    container_id = get_container_id_from_database(user, container_name)

    if not container_id:
        await interaction.response.send_message(embed=discord.Embed(description="### No instance found for your user.", color=0xff0000))
        return

    try:
        subprocess.run(["docker", "start", container_id], check=True)
        exec_cmd = await asyncio.create_subprocess_exec("docker", "exec", container_id, "tmate", "-F",
                                                        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        ssh_session_line = await capture_ssh_session_line(exec_cmd)
        if ssh_session_line:
            await interaction.user.send(embed=discord.Embed(description=f"### Instance Started\nSSH Session Command: ```{ssh_session_line}```", color=0x00ff00))
            await interaction.response.send_message(embed=discord.Embed(description="### Instance started successfully. Check your DMs for details.", color=0x00ff00))
        else:
            await interaction.response.send_message(embed=discord.Embed(description="### Instance started, but failed to get SSH session line.", color=0xff0000))
    except subprocess.CalledProcessError as e:
        await interaction.response.send_message(embed=discord.Embed(description=f"Error starting instance: {e}", color=0xff0000))

async def stop_server(interaction: discord.Interaction, container_name: str):
#    await interaction.response.defer()
    userid = str(interaction.user.id)
    container_id = get_container_id_from_database(user, container_name)

    if not container_id:
        await interaction.response.send_message(embed=discord.Embed(description="### No instance found for your user.", color=0xff0000))
        return

    try:
        subprocess.run(["docker", "stop", container_id], check=True)
        await interaction.response.send_message(embed=discord.Embed(description="### Instance stopped successfully.", color=0x00ff00))
    except subprocess.CalledProcessError as e:
        await interaction.response.send_message(embed=discord.Embed(description=f"### Error stopping instance: {e}", color=0xff0000))

async def restart_server(interaction: discord.Interaction, container_name: str):
#    await interaction.response.defer()
    userid = str(interaction.user.id)
    container_id = get_container_id_from_database(userid, container_name)

    if not container_id:
        await interaction.response.send_message(embed=discord.Embed(description="### No instance found for your user.", color=0xff0000))
        return

    try:
        subprocess.run(["docker", "restart", container_id], check=True)
        exec_cmd = await asyncio.create_subprocess_exec("docker", "exec", container_id, "tmate", "-F",
                                                        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        ssh_session_line = await capture_ssh_session_line(exec_cmd)
        if ssh_session_line:
            await interaction.user.send(embed=discord.Embed(description=f"### Instance Restarted\nSSH Session Command: ```{ssh_session_line}```\nOS: Ubuntu 22.04", color=0x00ff00))
            await interaction.response.send_message(embed=discord.Embed(description="### Instance restarted successfully. Check your DMs for details.", color=0x00ff00))
        else:
            await interaction.response.send_message(embed=discord.Embed(description="### Instance restarted, but failed to get SSH session line.", color=0xff0000))
    except subprocess.CalledProcessError as e:
        await interaction.response.send_message(embed=discord.Embed(description=f"Error restarting instance: {e}", color=0xff0000))

def get_container_id_from_database(userid, container_name):
    if not os.path.exists(database_file):
        return None
    with open(database_file, 'r') as f:
        for line in f:
            if line.startswith(userid) and container_name in line:
                return line.split('|')[1]
    return None

def generate_random_port():
    return random.randint(1025, 65535)

async def create_server_task(interaction):
    await interaction.response.send_message(embed=discord.Embed(description="### Creating Instance, This takes a few seconds. Powered by [CrashOfGuys](<https://discord.com/invite/VWm8zUEQN8>)", color=0x00ff00))
    userid = str(interaction.user.id)
    if count_user_servers(userid) >= SERVER_LIMIT:
        await interaction.followup.send(embed=discord.Embed(description="```Error: Instance Limit-reached```", color=0xff0000))
        return

    image = "ubuntu-22.04-with-tmate"

    try:
        container_id = subprocess.check_output([
           "docker", "run", "-itd", "--privileged", "--hostname", "crashcloud", "--cap-add=ALL", image
        ]).strip().decode('utf-8')
    except subprocess.CalledProcessError as e:
        await interaction.followup.send(embed=discord.Embed(description=f"### Error creating Docker container: {e}", color=0xff0000))
        return

    try:
        exec_cmd = await asyncio.create_subprocess_exec("docker", "exec", container_id, "tmate", "-F",
                                                        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        await interaction.followup.send(embed=discord.Embed(description=f"### Error executing tmate in Docker container: {e}", color=0xff0000))
        subprocess.run(["docker", "kill", container_id])
        subprocess.run(["docker", "rm", container_id])
        return

    ssh_session_line = await capture_ssh_session_line(exec_cmd)
    if ssh_session_line:
        await interaction.user.send(embed=discord.Embed(description=f"### Successfully created Instance\nSSH Session Command: ```{ssh_session_line}```\nOS: Ubuntu 22.04\nPassword: root", color=0x00ff00))
        add_to_database(userid, container_id, ssh_session_line)
        await interaction.followup.send(embed=discord.Embed(description="### Instance created successfully. Check your DMs for details.", color=0x00ff00))
    else:
        await interaction.followup.send(embed=discord.Embed(description="### Something went wrong or the Instance is taking longer than expected. If this problem continues, Contact Support.", color=0xff0000))
        subprocess.run(["docker", "kill", container_id])
        subprocess.run(["docker", "rm", container_id])

@bot.tree.command(name="deploy", description="Creates a new VPS Instance with customizable settings (Admin Only).")
@app_commands.describe(ram="Amount of RAM (e.g., 8g)", cores="Number of CPU cores", target_user="User ID to send VPS access", container_name="Custom container name")
async def deploy_ubuntu(interaction: discord.Interaction, ram: str, cores: int, target_user: str, container_name: str):
    userid = str(interaction.user.id)
    if userid not in {"1119657947434332211", "1085944828883369984"}:
        await interaction.response.send_message(embed=discord.Embed(description="🚫 **You do not have permission to use this command.**", color=0xff0000))
        return

    try:
        target_member = await bot.fetch_user(int(target_user))
        if not target_member:
            await interaction.response.send_message(embed=discord.Embed(description="❌ **Invalid user ID.**", color=0xff0000))
            return
    except discord.NotFound:
        await interaction.response.send_message(embed=discord.Embed(description="❌ **User not found.**", color=0xff0000))
        return

    await interaction.response.send_message(embed=discord.Embed(
        description=f"🛠️ **Creating VPS with:**\n- 💾 **RAM:** {ram}\n- 🔥 **Cores:** {cores}\n- 📦 **Container Name:** {container_name}\n\n⏳ **This may take a few seconds...**", 
        color=0x00ff00))

    try:
        container_id = subprocess.check_output([
            "docker", "run", "-itd", "--privileged", "--hostname", container_name, "--cap-add=ALL",
            "-m", ram, "--cpus", str(cores), "--name", container_name, "ubuntu-22.04-with-tmate"
        ]).strip().decode('utf-8')
        
        exec_cmd = await asyncio.create_subprocess_exec(
            "docker", "exec", container_id, "tmate", "-F",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        ssh_session_line = await capture_ssh_session_line(exec_cmd)

        if ssh_session_line:
            add_to_database(target_user, container_name, ssh_session_line)
            await target_member.send(embed=discord.Embed(
                description=f"✅ **Successfully Created VPS**\n\n```{ssh_session_line}```\n💾 **RAM:** {ram}\n🔥 **Cores:** {cores}\n📦 **Container Name:** {container_name}\n🖥️ **OS:** Ubuntu 22.04\n🔑 **Password:** root",
                color=0x00ff00))
            await interaction.followup.send(embed=discord.Embed(description="✅ **VPS created successfully. Check your DM for details.**", color=0x00ff00))
        else:
            raise Exception("Failed to capture SSH session.")
    
    except Exception as e:
        if container_id:
            subprocess.run(["docker", "kill", container_id])
            subprocess.run(["docker", "rm", container_id])
        await interaction.followup.send(embed=discord.Embed(description=f"❌ **Error creating VPS:** {e}", color=0xff0000))


# New Command: /nodedmin - Show all VPS details
@bot.tree.command(name="nodedmin", description="Shows all active VPS details (Admin Only).")
async def nodedmin(interaction: discord.Interaction):
    userid = str(interaction.user.id)
    if userid not in {"1119657947434332211", "1085944828883369984"}:
        await interaction.response.send_message(embed=discord.Embed(description="🚫 **You do not have permission to use this command.**", color=0xff0000))
        return
    
    if not os.path.exists(database_file):
        await interaction.response.send_message(embed=discord.Embed(description="🛑 **No active VPS instances found.**", color=0xff0000))
        return

    with open(database_file, 'r') as f:
        data = f.readlines()

    embed = discord.Embed(title="🌐 **Active VPS Details**", color=0x00ff00)
    for entry in data:
        user_id, container_name, ssh_command = entry.strip().split('|')
        embed.add_field(name=f"📦 **{container_name}**", value=f"👤 **User ID:** {user_id}\n🔑 **SSH:** `{ssh_command}`", inline=False)

    await interaction.response.send_message(embed=embed)


# New Command: /delvps - Delete a specific VPS
@bot.tree.command(name="delvps", description="Deletes a specified VPS container (Admin Only).")
@app_commands.describe(container_name="Name of the container to delete")
async def delvps(interaction: discord.Interaction, container_name: str):
    userid = str(interaction.user.id)
    if userid not in {"1119657947434332211", "1085944828883369984"}:
        await interaction.response.send_message(embed=discord.Embed(description="🚫 **You do not have permission to use this command.**", color=0xff0000))
        return
    
    container_id = get_container_id_from_database(userid, container_name)
    if not container_id:
        await interaction.response.send_message(embed=discord.Embed(description=f"❌ **No container named `{container_name}` found.**", color=0xff0000))
        return

    try:
        subprocess.run(["docker", "rm", "-f", container_name], check=True)
        remove_from_database(container_name)
        await interaction.response.send_message(embed=discord.Embed(description=f"✅ **Container `{container_name}` deleted successfully.**", color=0x00ff00))
    except subprocess.CalledProcessError as e:
        await interaction.response.send_message(embed=discord.Embed(description=f"❌ **Error deleting container:** {e}", color=0xff0000))


# Utility function to remove from database
def remove_from_database(container_name):
    if not os.path.exists(database_file):
        return
    with open(database_file, 'r') as f:
        lines = f.readlines()
    with open(database_file, 'w') as f:
        for line in lines:
            if container_name not in line:
                f.write(line)

# Utility function to fetch container ID
def get_container_id_from_database(userid, container_name):
    if not os.path.exists(database_file):
        return None
    with open(database_file, 'r') as f:
        for line in f:
            if line.startswith(userid) and container_name in line:
                return line.split('|')[1]
    return None

@bot.tree.command(name="ping", description="Check the bot's latency.")
async def ping(interaction: discord.Interaction):
    await interaction.response.defer()
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Latency: {latency}ms",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="list", description="Lists all your Instances")
async def list_servers(interaction: discord.Interaction):
    await interaction.response.defer()
    userid = str(interaction.user.id)
    servers = get_user_servers(userid)
    if servers:
        embed = discord.Embed(title="Your Instances", color=0x00ff00)
        for server in servers:
            _, container_name, _ = server.split('|')
            embed.add_field(name=container_name, value="32GB RAM - Premuim - 4 cores", inline=False)
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(embed=discord.Embed(description="You have no servers.", color=0xff0000))

async def execute_command(command):
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    return stdout.decode(), stderr.decode()

PUBLIC_IP = '138.68.79.95'

async def capture_output(process, keyword):
    while True:
        output = await process.stdout.readline()
        if not output:
            break
        output = output.decode('utf-8').strip()
        if keyword in output:
            return output
    return None


@bot.tree.command(name="help", description="Shows the help message")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="help", color=0x00ff00)
    embed.add_field(name="/deploy", value="Creates a new Instance with Ubuntu 22.04.", inline=False)
    embed.add_field(name="/remove <ssh_command/Name>", value="Removes a server", inline=False)
    embed.add_field(name="/start <ssh_command/Name>", value="Start a server.", inline=False)
    embed.add_field(name="/stop <ssh_command/Name>", value="Stop a server.", inline=False)
    embed.add_field(name="/regen-ssh <ssh_command/Name>", value="Regenerates SSH cred", inline=False)
    embed.add_field(name="/restart <ssh_command/Name>", value="Stop a server.", inline=False)
    embed.add_field(name="/list", value="List all your servers", inline=False)
    embed.add_field(name="/ping", value="Check the bot's latency.", inline=False)
    embed.add_field(name="/node", value="Check The Node Storage Usage.", inline=False)
    embed.add_field(name="/bal", value="Check Your Balance.", inline=False)
    embed.add_field(name="/renew", value="Renew The VPS.", inline=False)
    embed.add_field(name="/earncredit", value="earn the credit.", inline=False)
    await interaction.response.send_message(embed=embed)


# run the bot
bot.run(TOKEN)
