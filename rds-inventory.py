#!/usr/bin/env python3
import json
import pymysql
import os
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
            # Modify this query according to your database schema
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
        inventory[region_group]['hosts'].append(host['hostname'])
    
    return inventory

def main():
    inventory = build_inventory()
    print(json.dumps(inventory, indent=2))

if __name__ == '__main__':
    main()
