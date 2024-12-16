from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from database import DynamicDatabase
from auth import login_required, admin_required
import os
import json
import sqlite3
import csv

app = Flask(__name__, 
            template_folder=os.path.join(os.path.dirname(__file__), 'templates'))
app.secret_key = os.urandom(24)
db = DynamicDatabase()

@app.route('/')
def dashboard():
    # If user is not logged in, redirect to login
    if 'user' not in session:
        return redirect(url_for('login'))
    
    # Fetch entities for the dashboard
    try:
        entities = db.get_entities()
        return render_template('dashboard.html', 
                               entities=entities, 
                               role=session.get('role', 'user'))
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'danger')
        return redirect(url_for('login'))

@app.route('/entity-types/new', methods=['GET', 'POST'])
@login_required
def create_entity_type():
    if request.method == 'POST':
        type_name = request.form['type_name']
        attributes = request.form.getlist('attributes')
        
        try:
            db.create_entity_type(type_name, attributes)
            flash(f'Entity type {type_name} created successfully', 'success')
            return redirect(url_for('list_entity_types'))
        except Exception as e:
            flash(f'Error creating entity type: {str(e)}', 'danger')
    
    entity_types = db.get_entity_types()
    return render_template('entity_type_form.html', entity_types=entity_types)

@app.route('/entity-types')
@login_required
def list_entity_types():
    entity_types = db.get_entity_types()
    return render_template('entity_types_list.html', entity_types=entity_types)

@app.route('/entities/new', methods=['GET', 'POST'])
@login_required
def create_entity():
    entity_types = db.get_entity_types()
    
    if request.method == 'POST':
        entity_type = request.form['entity_type']
        
        # Dynamically collect all form data except entity_type
        data = {k: v for k, v in request.form.items() if k != 'entity_type'}
        
        try:
            entity_id = db.create_entity(entity_type, data)
            flash(f'Entity created successfully with ID {entity_id}', 'success')
            return redirect(url_for('list_entities'))
        except Exception as e:
            flash(f'Error creating entity: {str(e)}', 'danger')
    
    return render_template('dynamic_entity_form.html', entity_types=entity_types)

@app.route('/entities')
@login_required
def list_entities():
    entities = db.get_entities()
    return render_template('entities_list.html', entities=entities)

@app.route('/entities/edit/<int:entity_id>', methods=['GET', 'POST'])
@login_required
def edit_entity(entity_id):
    entity = db.get_entity_by_id(entity_id)
    
    if request.method == 'POST':
        # Dynamically collect all form data
        data = {k: v for k, v in request.form.items() if k != 'entity_type'}
        
        try:
            db.update_entity(entity_id, data)
            flash('Entity updated successfully', 'success')
            return redirect(url_for('list_entities'))
        except Exception as e:
            flash(f'Error updating entity: {str(e)}', 'danger')
    
    return render_template('dynamic_entity_form.html', 
                           entity=entity, 
                           edit_mode=True)

@app.route('/entities/delete/<int:entity_id>', methods=['POST'])
@login_required
def delete_entity(entity_id):
    try:
        db.delete_entity(entity_id)
        flash('Entity deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting entity: {str(e)}', 'danger')
    
    return redirect(url_for('list_entities'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Implement your authentication logic here
        # This is a placeholder - replace with actual authentication
        if username == 'admin' and password == 'admin123':
            session['user'] = username
            session['role'] = 'admin'
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/export/entity-types')
@login_required
def export_entity_types():
    try:
        # Get entity types
        entity_types = db.get_entity_types()
        
        # Create export directory if it doesn't exist
        export_dir = os.path.join(os.path.dirname(__file__), 'exports')
        os.makedirs(export_dir, exist_ok=True)
        
        # Generate filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_path = os.path.join(export_dir, f'entity_types_{timestamp}.csv')
        
        # Export to CSV
        with open(export_path, 'w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(['Name', 'Attributes'])
            
            for entity_type in entity_types:
                csvwriter.writerow([
                    entity_type['name'], 
                    ', '.join(entity_type['attributes'])
                ])
        
        flash(f'Entity types exported to {export_path}', 'success')
        return redirect(url_for('list_entity_types'))
    
    except Exception as e:
        flash(f'Error exporting entity types: {str(e)}', 'danger')
        return redirect(url_for('list_entity_types'))

@app.route('/export/entities')
@login_required
def export_entities():
    try:
        # Get all entities
        entities = db.get_entities()
        
        # Create export directory if it doesn't exist
        export_dir = os.path.join(os.path.dirname(__file__), 'exports')
        os.makedirs(export_dir, exist_ok=True)
        
        # Generate filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_path = os.path.join(export_dir, f'entities_{timestamp}.csv')
        
        # Export to CSV
        with open(export_path, 'w', newline='') as csvfile:
            # Dynamically create headers based on first entity's keys
            if entities:
                headers = ['ID', 'Type'] + list(entities[0]['data'].keys())
                csvwriter = csv.writer(csvfile)
                csvwriter.writerow(headers)
                
                for entity in entities:
                    row = [
                        entity['id'], 
                        entity['type']
                    ] + [entity['data'].get(key, '') for key in headers[2:]]
                    csvwriter.writerow(row)
        
        flash(f'Entities exported to {export_path}', 'success')
        return redirect(url_for('list_entities'))
    
    except Exception as e:
        flash(f'Error exporting entities: {str(e)}', 'danger')
        return redirect(url_for('list_entities'))

@app.route('/database-location')
@login_required
def show_database_location():
    db_path = os.path.join(os.path.dirname(__file__), 'crm.db')
    return render_template('database_location.html', db_path=db_path)

if __name__ == '__main__':
    app.run(debug=True)

import os
print("Current Working Directory:", os.getcwd())
print("Template Directory:", os.path.join(os.path.dirname(__file__), 'templates'))
print("Template Files:", os.listdir(os.path.join(os.path.dirname(__file__), 'templates')))