#!/usr/bin/env python3
import json # json
import pymysql
import os
import sys
from datetime import datetime

def get_db_connection():
    # Get database credentials from environment variables
    db_host = os.getenv('DB_HOST', 'localhost')
    db_user = os.getenv('DB_USER', 'user')
    db_pass = os.getenv('DB_PASS', 'password')
    db_name = os.getenv('DB_NAME', 'inventory_db')
    
    return pymysql.connect(
        host=db_host,
        user=db_user,
        password=db_pass,
        database=db_name
    )

def get_hosts_from_db():
    conn = get_db_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("""
                SELECT 
                    h.hostname,
                    h.ip_address,
                    h.environment,
                    h.role,
                    h.ssh_user,
                    h.ssh_port,
                    h.region
                FROM hosts h
                WHERE h.active = 1
            """)
            return cursor.fetchall()
    finally:
        conn.close()

def build_inventory():
    hosts = get_hosts_from_db()
    inventory = {
        '_meta': {
            'hostvars': {}
        }
    }
    
    # Initialize groups
    environments = set()
    roles = set()
    regions = set()
    
    # Process each host
    for host in hosts:
        # Add host vars
        inventory['_meta']['hostvars'][host['hostname']] = {
            'ansible_host': host['ip_address'],
            'ansible_user': host['ssh_user'],
            'ansible_port': host['ssh_port']
        }
        
        # Add to environment group
        if host['environment'] not in inventory:
            inventory[host['environment']] = {'hosts': []}
        inventory[host['environment']]['hosts'].append(host['hostname'])
        
        # Add to role group
        role_group = f"role_{host['role']}"
        if role_group not in inventory:
            inventory[role_group] = {'hosts': []}
        inventory[role_group]['hosts'].append(host['hostname'])
        
        # Add to region group
        region_group = f"region_{host['region']}"
        if region_group not in inventory:
            inventory[region_group] = {'hosts': []}
        region_group['hosts'].append(host['hostname'])
    
    return inventory

def empty_inventory():
    return {'_meta': {'hostvars': {}}}

def host_vars(hostname):
    """Return variables for a specific host"""
    hosts = get_hosts_from_db()
    for host in hosts:
        if host['hostname'] == hostname:
            return {
                'ansible_host': host['ip_address'],
                'ansible_user': host['ssh_user'],
                'ansible_port': host['ssh_port']
            }
    return {}

def main():
    # Make sure script is executable
    if not os.access(__file__, os.X_OK):
        os.chmod(__file__, 0o755)

    # Add argument handling as required by Ansible
    if len(sys.argv) == 2 and sys.argv[1] == '--list':
        inventory = build_inventory()
        print(json.dumps(inventory))
    elif len(sys.argv) == 3 and sys.argv[1] == '--host':
        vars = host_vars(sys.argv[2])
        print(json.dumps(vars))
    else:
        sys.stderr.write("Usage: %s --list or --host <hostname>\n" % sys.argv[0])
        sys.exit(1)

if __name__ == '__main__':
    main()
