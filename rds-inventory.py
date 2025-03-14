#!/usr/bin/env python3
import json
import psycopg2
import psycopg2.extras
import os
import sys
from datetime import datetime

def get_db_connection():
    # Get database credentials from environment variables
    db_host = os.getenv('DB_HOST', 'localhost')
    db_user = os.getenv('DB_USER', 'user')
    db_pass = os.getenv('DB_PASS', 'password')
    db_name = os.getenv('DB_NAME', 'inventory_db')
    db_port = os.getenv('DB_PORT', '5432')
    
    return psycopg2.connect(
        host=db_host,
        user=db_user,
        password=db_pass,
        dbname=db_name,
        port=db_port
    )

def get_hosts_from_db():
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
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
                WHERE h.active = true
            """)
            # Convert DictRow objects to regular dictionaries
            return [dict(row) for row in cursor.fetchall()]
    except psycopg2.Error as e:
        print(f"Database error: {e}", file=sys.stderr)
        return []
    finally:
        conn.close()

def build_inventory():
    try:
        hosts = get_hosts_from_db()
        inventory = {
            '_meta': {
                'hostvars': {}
            }
        }
        
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
            inventory[region_group]['hosts'].append(host['hostname'])
        
        return inventory
    except Exception as e:
        print(f"Error building inventory: {e}", file=sys.stderr)
        return empty_inventory()

def empty_inventory():
    return {'_meta': {'hostvars': {}}}

def host_vars(hostname):
    """Return variables for a specific host"""
    try:
        hosts = get_hosts_from_db()
        for host in hosts:
            if host['hostname'] == hostname:
                return {
                    'ansible_host': host['ip_address'],
                    'ansible_user': host['ssh_user'],
                    'ansible_port': host['ssh_port']
                }
        return {}
    except Exception as e:
        print(f"Error getting host vars: {e}", file=sys.stderr)
        return {}

def main():
    # Make sure script is executable
    if not os.access(__file__, os.X_OK):
        os.chmod(__file__, 0o755)

    try:
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
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
