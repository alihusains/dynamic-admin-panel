import sqlite3
import json
import os

class DynamicDatabase:
    def __init__(self, db_path='crm.db'):
        self.db_path = os.path.join(os.path.dirname(__file__), db_path)
        self.conn = None
        self.cursor = None
        self.setup_database()

    def connect(self):
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

    def close(self):
        if self.conn:
            self.conn.close()

    def setup_database(self):
        self.connect()
        # Create a table to track dynamic entity types
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS entity_types (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                attributes TEXT NOT NULL
            )
        ''')

        # Create a table to track all dynamic entities
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS dynamic_entities (
                id INTEGER PRIMARY KEY,
                type TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.conn.commit()
        self.close()

    def create_entity_type(self, type_name, attributes):
        """
        Create a new entity type with specified attributes
        """
        self.connect()
        try:
            # Ensure attributes is a JSON string
            if isinstance(attributes, list):
                attributes = json.dumps(attributes)
            
            self.cursor.execute('''
                INSERT OR REPLACE INTO entity_types (name, attributes) 
                VALUES (?, ?)
            ''', (type_name, attributes))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            print(f"Entity type {type_name} already exists")
            return False
        finally:
            self.close()

    def get_entity_types(self):
        """
        Retrieve all defined entity types
        """
        self.connect()
        self.cursor.execute('SELECT name, attributes FROM entity_types')
        types = [
            {
                'name': row[0], 
                'attributes': json.loads(row[1])
            } 
            for row in self.cursor.fetchall()
        ]
        self.close()
        return types

    def create_entity(self, type_name, data):
        """
        Create a new entity of a specific type
        """
        self.connect()
        try:
            # Validate entity type exists
            self.cursor.execute('SELECT attributes FROM entity_types WHERE name = ?', (type_name,))
            type_record = self.cursor.fetchone()
            
            if not type_record:
                raise ValueError(f"Entity type {type_name} does not exist")
            
            # Store data as JSON
            json_data = json.dumps(data)
            
            self.cursor.execute('''
                INSERT INTO dynamic_entities (type, data) 
                VALUES (?, ?)
            ''', (type_name, json_data))
            
            entity_id = self.cursor.lastrowid
            self.conn.commit()
            return entity_id
        
        except Exception as e:
            self.conn.rollback()
            print(f"Error creating entity: {e}")
            raise
        finally:
            self.close()

    def get_entities(self, type_name=None):
        """
        Retrieve entities, optionally filtered by type
        """
        self.connect()
        try:
            if type_name:
                self.cursor.execute('''
                    SELECT id, type, data 
                    FROM dynamic_entities 
                    WHERE type = ?
                ''', (type_name,))
            else:
                self.cursor.execute('''
                    SELECT id, type, data 
                    FROM dynamic_entities
                ''')
            
            entities = [
                {
                    'id': row[0],
                    'type': row[1],
                    'data': json.loads(row[2])
                }
                for row in self.cursor.fetchall()
            ]
            return entities
        finally:
            self.close()

    def get_entity_by_id(self, entity_id):
        """
        Retrieve a specific entity by its ID
        """
        self.connect()
        try:
            self.cursor.execute('''
                SELECT id, type, data 
                FROM dynamic_entities 
                WHERE id = ?
            ''', (entity_id,))
            
            row = self.cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'type': row[1],
                    'data': json.loads(row[2])
                }
            return None
        finally:
            self.close()

    def update_entity(self, entity_id, data):
        """
        Update an existing entity
        """
        self.connect()
        try:
            # Retrieve current entity to validate type
            current_entity = self.get_entity_by_id(entity_id)
            if not current_entity:
                raise ValueError("Entity not found")

            # Merge existing data with new data
            updated_data = {**current_entity['data'], **data}
            
            # Update entity
            self.cursor.execute('''
                UPDATE dynamic_entities 
                SET data = ? 
                WHERE id = ?
            ''', (json.dumps(updated_data), entity_id))
            
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"Error updating entity: {e}")
            raise
        finally:
            self.close()

    def delete_entity(self, entity_id):
        """
        Delete an entity by its ID
        """
        self.connect()
        try:
            self.cursor.execute('''
                DELETE FROM dynamic_entities 
                WHERE id = ?
            ''', (entity_id,))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"Error deleting entity: {e}")
            raise
        finally:
            self.close()