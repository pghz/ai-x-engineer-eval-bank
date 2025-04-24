import streamlit as st
import pandas as pd
import os
import requests
import json
from datetime import datetime

# Supabase config
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
except (KeyError, FileNotFoundError):
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")

try:
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except (KeyError, FileNotFoundError):
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# Supabase REST API helper
def supabase_request(method, endpoint, params=None, data=None):
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    
    try:
        if method.lower() == "get":
            response = requests.get(url, headers=headers, params=params)
        elif method.lower() == "post":
            response = requests.post(url, headers=headers, json=data)
        elif method.lower() == "put":
            response = requests.put(url, headers=headers, json=data)
        elif method.lower() == "patch":
            # Ensure we have a WHERE clause for PATCH/UPDATE
            if not params:
                st.error("Update requires a WHERE clause")
                return None
            response = requests.patch(url, headers=headers, json=data, params=params)
        elif method.lower() == "delete":
            # Ensure we have a WHERE clause for DELETE
            if not params:
                st.error("Delete requires a WHERE clause")
                return None
            response = requests.delete(url, headers=headers, params=params)
        else:
            st.error(f"Invalid method: {method}")
            return None
        
        if response.status_code >= 400:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
        
        return response.json()
    except Exception as e:
        st.error(f"Request error: {str(e)}")
        return None

# Get Supabase client
def get_supabase_client():
    if 'supabase_url' in st.session_state and 'supabase_key' in st.session_state:
        global SUPABASE_URL, SUPABASE_KEY
        SUPABASE_URL = st.session_state.supabase_url
        SUPABASE_KEY = st.session_state.supabase_key
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        st.error("Configure credentials first")
        st.stop()
    
    try:
        test = supabase_request("get", "ai_personas", params={"limit": 1})
        if test is None:
            st.error("Connection failed")
            st.stop()
        return True
    except Exception as e:
        st.error(f"Connection failed: {str(e)}")
        st.stop()

# Check if tables exist
def initialize_database():
    try:
        result = supabase_request("get", "ai_personas", params={"limit": 1})
        if result is not None:
            st.sidebar.success("✅ Tables ready")
            return True
        
        st.sidebar.warning("Database not connected")
        return False
    except Exception as e:
        st.sidebar.warning("Database not connected")
        return False

# SQL script for table creation
def get_table_creation_sql():
    return """
-- First, drop all tables in reverse order of dependencies
DROP TABLE IF EXISTS evaluations;
DROP TABLE IF EXISTS answers;
DROP TABLE IF EXISTS questions;
DROP TABLE IF EXISTS question_threads;
DROP TABLE IF EXISTS question_categories;
DROP TABLE IF EXISTS ai_personas;

-- Now recreate all the tables with the correct schema

-- AI Personas table
CREATE TABLE IF NOT EXISTS ai_personas (
    persona_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_by TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Question Categories table
CREATE TABLE IF NOT EXISTS question_categories (
    category_id SERIAL PRIMARY KEY,
    persona_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    created_by TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (persona_id) REFERENCES ai_personas(persona_id) ON DELETE CASCADE
);

-- Question Threads table
CREATE TABLE IF NOT EXISTS question_threads (
    thread_id SERIAL PRIMARY KEY,
    category_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    created_by TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES question_categories(category_id) ON DELETE CASCADE
);

-- Questions table
CREATE TABLE IF NOT EXISTS questions (
    question_id SERIAL PRIMARY KEY,
    thread_id INTEGER NOT NULL,
    sequence_number INTEGER NOT NULL,
    content TEXT NOT NULL,
    reference_links TEXT,
    created_by TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (thread_id) REFERENCES question_threads(thread_id) ON DELETE CASCADE
);

-- Answers table
CREATE TABLE IF NOT EXISTS answers (
    answer_id SERIAL PRIMARY KEY,
    question_id INTEGER NOT NULL,
    is_ai_generated BOOLEAN NOT NULL,
    content TEXT NOT NULL,
    metadata TEXT,
    created_by TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (question_id) REFERENCES questions(question_id) ON DELETE CASCADE
);

-- Evaluations table
CREATE TABLE IF NOT EXISTS evaluations (
    evaluation_id SERIAL PRIMARY KEY,
    answer_id INTEGER NOT NULL,
    dimension TEXT NOT NULL,
    score REAL NOT NULL,
    comments TEXT,
    evaluator TEXT,
    created_by TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (answer_id) REFERENCES answers(answer_id) ON DELETE CASCADE
);
"""

# CRUD operations for each table
class PersonaManager:
    @staticmethod
    def create(name, description="", created_by=""):
        data = {
            "name": name,
            "description": description,
            "created_by": created_by
        }
        result = supabase_request("post", "ai_personas", data=data)
        if result and len(result) > 0:
            return result[0]['persona_id']
        return None
    
    @staticmethod
    def get_all():
        result = supabase_request("get", "ai_personas", params={"order": "name"})
        return pd.DataFrame(result) if result else pd.DataFrame()
    
    @staticmethod
    def get_by_id(persona_id):
        result = supabase_request("get", f"ai_personas", params={"persona_id": f"eq.{persona_id}"})
        return pd.DataFrame(result) if result else pd.DataFrame()
    
    @staticmethod
    def update(persona_id, name, description, updated_by=""):
        data = {
            "name": name,
            "description": description,
            "updated_by": updated_by,
            "updated_at": datetime.now().isoformat()
        }
        supabase_request("patch", f"ai_personas", params={"persona_id": f"eq.{persona_id}"}, data=data)
    
    @staticmethod
    def delete(persona_id):
        supabase_request("delete", f"ai_personas", params={"persona_id": f"eq.{persona_id}"})

class CategoryManager:
    @staticmethod
    def create(persona_id, name, description="", created_by=""):
        data = {
            "persona_id": persona_id,
            "name": name,
            "description": description,
            "created_by": created_by
        }
        result = supabase_request("post", "question_categories", data=data)
        if result and len(result) > 0:
            return result[0]['category_id']
        return None
    
    @staticmethod
    def get_by_persona(persona_id):
        result = supabase_request("get", "question_categories", 
                                params={"persona_id": f"eq.{persona_id}", "order": "name"})
        return pd.DataFrame(result) if result else pd.DataFrame()
    
    @staticmethod
    def get_by_id(category_id):
        result = supabase_request("get", "question_categories", 
                                params={"category_id": f"eq.{category_id}"})
        return pd.DataFrame(result) if result else pd.DataFrame()
    
    @staticmethod
    def update(category_id, name, description, updated_by=""):
        data = {
            "name": name,
            "description": description,
            "updated_by": updated_by,
            "updated_at": datetime.now().isoformat()
        }
        supabase_request("patch", "question_categories", 
                       params={"category_id": f"eq.{category_id}"}, 
                       data=data)
    
    @staticmethod
    def delete(category_id):
        supabase_request("delete", "question_categories", 
                       params={"category_id": f"eq.{category_id}"})

class ThreadManager:
    @staticmethod
    def create(category_id, name, description="", created_by=""):
        data = {
            "category_id": category_id,
            "name": name,
            "description": description,
            "created_by": created_by
        }
        result = supabase_request("post", "question_threads", data=data)
        if result and len(result) > 0:
            return result[0]['thread_id']
        return None
    
    @staticmethod
    def get_by_category(category_id):
        result = supabase_request("get", "question_threads", 
                                params={"category_id": f"eq.{category_id}", "order": "name"})
        return pd.DataFrame(result) if result else pd.DataFrame()
    
    @staticmethod
    def get_by_id(thread_id):
        result = supabase_request("get", "question_threads", 
                                params={"thread_id": f"eq.{thread_id}"})
        return pd.DataFrame(result) if result else pd.DataFrame()
    
    @staticmethod
    def update(thread_id, name, description, updated_by=""):
        data = {
            "name": name,
            "description": description,
            "updated_by": updated_by,
            "updated_at": datetime.now().isoformat()
        }
        supabase_request("patch", "question_threads", 
                       params={"thread_id": f"eq.{thread_id}"}, 
                       data=data)
    
    @staticmethod
    def delete(thread_id):
        supabase_request("delete", "question_threads", 
                       params={"thread_id": f"eq.{thread_id}"})

class QuestionManager:
    @staticmethod
    def create(thread_id, content, reference_links="", created_by="", sequence_number=None):
        if sequence_number is None:
            result = supabase_request("get", "questions", 
                                    params={"thread_id": f"eq.{thread_id}", "order": "sequence_number.desc", "limit": 1})
            sequence_number = 1
            if result and len(result) > 0:
                sequence_number = result[0]['sequence_number'] + 1
        
        data = {
            "thread_id": thread_id,
            "sequence_number": sequence_number,
            "content": content,
            "reference_links": reference_links,
            "created_by": created_by
        }
        result = supabase_request("post", "questions", data=data)
        if result and len(result) > 0:
            question_id = result[0]['question_id']
            QuestionManager.reorder(thread_id)
            return question_id
        return None
    
    @staticmethod
    def get_by_thread(thread_id):
        result = supabase_request("get", "questions", 
                                params={"thread_id": f"eq.{thread_id}", "order": "sequence_number"})
        return pd.DataFrame(result) if result else pd.DataFrame()
    
    @staticmethod
    def get_by_id(question_id):
        result = supabase_request("get", "questions", 
                                params={"question_id": f"eq.{question_id}"})
        return pd.DataFrame(result) if result else pd.DataFrame()
    
    @staticmethod
    def update(question_id, content, reference_links=None, updated_by="", sequence_number=None):
        data = {
            "content": content,
            "updated_by": updated_by,
            "updated_at": datetime.now().isoformat()
        }
        
        if reference_links is not None:
            data["reference_links"] = reference_links
            
        if sequence_number is not None:
            data["sequence_number"] = sequence_number
        
        supabase_request("patch", "questions", 
                       params={"question_id": f"eq.{question_id}"}, 
                       data=data)
    
    @staticmethod
    def delete(question_id):
        question = QuestionManager.get_by_id(question_id)
        if not question.empty:
            thread_id = question.iloc[0]['thread_id']
            supabase_request("delete", "questions", params={"question_id": f"eq.{question_id}"})
            QuestionManager.reorder(thread_id)
    
    @staticmethod
    def reorder(thread_id):
        questions = QuestionManager.get_by_thread(thread_id)
        if questions.empty:
            return
        
        for idx, row in enumerate(questions.itertuples(), 1):
            if row.sequence_number != idx:
                supabase_request("patch", "questions", 
                               params={"question_id": f"eq.{row.question_id}"}, 
                               data={"sequence_number": idx})

class AnswerManager:
    @staticmethod
    def create(question_id, content, is_ai_generated=True, metadata="", created_by=""):
        data = {
            "question_id": question_id,
            "is_ai_generated": is_ai_generated,
            "content": content,
            "metadata": metadata,
            "created_by": created_by
        }
        result = supabase_request("post", "answers", data=data)
        if result and len(result) > 0:
            return result[0]['answer_id']
        return None
    
    @staticmethod
    def get_by_question(question_id):
        result = supabase_request("get", "answers", 
                                params={"question_id": f"eq.{question_id}", "order": "created_at"})
        return pd.DataFrame(result) if result else pd.DataFrame()
    
    @staticmethod
    def get_by_id(answer_id):
        result = supabase_request("get", "answers", 
                                params={"answer_id": f"eq.{answer_id}"})
        return pd.DataFrame(result) if result else pd.DataFrame()
    
    @staticmethod
    def update(answer_id, content, is_ai_generated=None, metadata=None, updated_by=""):
        data = {
            "content": content,
            "updated_by": updated_by,
            "updated_at": datetime.now().isoformat()
        }
        
        if is_ai_generated is not None:
            data["is_ai_generated"] = is_ai_generated
        
        if metadata is not None:
            data["metadata"] = metadata
        
        supabase_request("patch", "answers", 
                       params={"answer_id": f"eq.{answer_id}"}, 
                       data=data)
    
    @staticmethod
    def delete(answer_id):
        supabase_request("delete", "answers", params={"answer_id": f"eq.{answer_id}"})

class EvaluationManager:
    @staticmethod
    def create(answer_id, dimension, score, comments="", evaluator="", created_by=""):
        data = {
            "answer_id": answer_id,
            "dimension": dimension,
            "score": score,
            "comments": comments,
            "evaluator": evaluator,
            "created_by": created_by
        }
        result = supabase_request("post", "evaluations", data=data)
        if result and len(result) > 0:
            return result[0]['evaluation_id']
        return None
    
    @staticmethod
    def get_by_answer(answer_id):
        result = supabase_request("get", "evaluations", 
                                params={"answer_id": f"eq.{answer_id}", "order": "dimension"})
        return pd.DataFrame(result) if result else pd.DataFrame()
    
    @staticmethod
    def get_dimensions_for_answer(answer_id):
        result = supabase_request("get", "evaluations", 
                                params={"answer_id": f"eq.{answer_id}", "select": "dimension"})
        return [row['dimension'] for row in result] if result else []
    
    @staticmethod
    def get_by_id(evaluation_id):
        result = supabase_request("get", "evaluations", 
                                params={"evaluation_id": f"eq.{evaluation_id}"})
        return pd.DataFrame(result) if result else pd.DataFrame()
    
    @staticmethod
    def update(evaluation_id, dimension=None, score=None, comments=None, evaluator=None, updated_by=""):
        data = {
            "updated_by": updated_by,
            "updated_at": datetime.now().isoformat()
        }
        
        if dimension is not None:
            data["dimension"] = dimension
        
        if score is not None:
            data["score"] = score
        
        if comments is not None:
            data["comments"] = comments
        
        if evaluator is not None:
            data["evaluator"] = evaluator
        
        supabase_request("patch", "evaluations", 
                       params={"evaluation_id": f"eq.{evaluation_id}"}, 
                       data=data)
    
    @staticmethod
    def delete(evaluation_id):
        supabase_request("delete", "evaluations", 
                       params={"evaluation_id": f"eq.{evaluation_id}"})

# UI functions
def persona_page():
    st.header("AI Engineer Personas")
    
    # Form for adding a new persona
    with st.expander("Add New Persona"):
        with st.form("add_persona_form"):
            name = st.text_input("Persona Name")
            author = st.text_input("Created By (optional)")
            description = st.text_area("Description (optional)", height=100)
            submit_button = st.form_submit_button("Add Persona")
            
            if submit_button and name:
                try:
                    # Pass the created_by parameter
                    PersonaManager.create(name, description, author)
                    st.success(f"Added persona: {name}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding persona: {str(e)}")
    
    # Display and manage existing personas
    try:
        personas = PersonaManager.get_all()
        if not personas.empty:
            for _, row in personas.iterrows():
                with st.expander(f"{row['name']}"):
                    # Display persona details with creator info
                    st.write(f"**Description:** {row['description']}")
                    
                    # Show creator information if available
                    if 'created_by' in row and row['created_by']:
                        st.write(f"**Created By:** {row['created_by']}")
                    st.write(f"**Created:** {row['created_at']}")
                    
                    # Show updater information if available
                    if 'updated_by' in row and row['updated_by']:
                        st.write(f"**Updated By:** {row['updated_by']}")
                    st.write(f"**Updated:** {row['updated_at']}")
                    
                    # Edit form
                    form_key = f"edit_persona_{row['persona_id']}"
                    with st.form(form_key):
                        edit_name = st.text_input("Name", value=row['name'])
                        edit_author = st.text_input("Updated By (optional)")
                        edit_desc = st.text_area("Description (optional)", value=row['description'], height=100)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            update_button = st.form_submit_button("Update")
                        with col2:
                            delete_button = st.form_submit_button("Delete")
                    
                    if update_button and edit_name:
                        try:
                            # Pass the updated_by parameter
                            PersonaManager.update(row['persona_id'], edit_name, edit_desc, edit_author)
                            st.success("Updated successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error updating persona: {str(e)}")
                    
                    if delete_button:
                        try:
                            PersonaManager.delete(row['persona_id'])
                            st.success("Deleted successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error deleting persona: {str(e)}")
        else:
            st.info("No personas have been added yet.")
    except Exception as e:
        st.error(f"Error loading personas: {str(e)}")

def category_page():
    st.header("Question Categories")
    
    try:
        # Get all personas for selection
        personas = PersonaManager.get_all()
        if personas.empty:
            st.warning("Please add an AI Persona first.")
            return
        
        # Select a persona to see its categories - use session state to remember last selection
        if 'last_persona_id' not in st.session_state:
            st.session_state.last_persona_id = personas['persona_id'].iloc[0] if not personas.empty else None
            
        persona_id = st.selectbox(
            "Select AI Persona",
            options=personas['persona_id'].tolist(),
            format_func=lambda x: personas.loc[personas['persona_id'] == x, 'name'].iloc[0],
            index=personas['persona_id'].tolist().index(st.session_state.last_persona_id) if st.session_state.last_persona_id in personas['persona_id'].values else 0
        )
        st.session_state.last_persona_id = persona_id
        
        persona_name = personas.loc[personas['persona_id'] == persona_id, 'name'].iloc[0]
        st.subheader(f"Categories for: {persona_name}")
        
        # Form for adding a new category
        with st.expander("Add New Category"):
            with st.form("add_category_form"):
                name = st.text_input("Category Name")
                author = st.text_input("Created By (optional)")
                description = st.text_area("Description (optional)", height=100)
                submit_button = st.form_submit_button("Add Category")
                
                if submit_button and name:
                    try:
                        # Pass created_by parameter
                        CategoryManager.create(persona_id, name, description, author)
                        st.success(f"Added category: {name}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding category: {str(e)}")
        
        # Display and manage existing categories
        categories = CategoryManager.get_by_persona(persona_id)
        if not categories.empty:
            for _, row in categories.iterrows():
                with st.expander(f"{row['name']}"):
                    # Display category details
                    st.write(f"**Description:** {row['description']}")
                    
                    # Show creator information if available
                    if 'created_by' in row and row['created_by']:
                        st.write(f"**Created By:** {row['created_by']}")
                    st.write(f"**Created:** {row['created_at']}")
                    
                    # Show updater information if available
                    if 'updated_by' in row and row['updated_by']:
                        st.write(f"**Updated By:** {row['updated_by']}")
                    st.write(f"**Updated:** {row['updated_at']}")
                    
                    # Edit form
                    form_key = f"edit_category_{row['category_id']}"
                    with st.form(form_key):
                        edit_name = st.text_input("Name", value=row['name'])
                        edit_author = st.text_input("Updated By (optional)")
                        edit_desc = st.text_area("Description (optional)", value=row['description'], height=100)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            update_button = st.form_submit_button("Update")
                        with col2:
                            delete_button = st.form_submit_button("Delete")
                    
                    if update_button and edit_name:
                        try:
                            # Pass updated_by parameter
                            CategoryManager.update(row['category_id'], edit_name, edit_desc, edit_author)
                            st.success("Updated successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error updating category: {str(e)}")
                    
                    if delete_button:
                        try:
                            CategoryManager.delete(row['category_id'])
                            st.success("Deleted successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error deleting category: {str(e)}")
        else:
            st.info(f"No categories have been added for {persona_name} yet.")
    except Exception as e:
        st.error(f"Error on categories page: {str(e)}")

def thread_page():
    st.header("Question Threads")
    
    try:
        # Get all personas for selection
        personas = PersonaManager.get_all()
        if personas.empty:
            st.warning("Please add an AI Persona first.")
            return
        
        # Select a persona to see its categories - use session state to remember last selection
        if 'last_persona_id' not in st.session_state:
            st.session_state.last_persona_id = personas['persona_id'].iloc[0] if not personas.empty else None
            
        persona_id = st.selectbox(
            "Select AI Persona",
            options=personas['persona_id'].tolist(),
            format_func=lambda x: personas.loc[personas['persona_id'] == x, 'name'].iloc[0],
            index=personas['persona_id'].tolist().index(st.session_state.last_persona_id) if st.session_state.last_persona_id in personas['persona_id'].values else 0
        )
        st.session_state.last_persona_id = persona_id
        
        # Get categories for the selected persona
        categories = CategoryManager.get_by_persona(persona_id)
        if categories.empty:
            st.warning(f"Please add Categories for the selected persona first.")
            return
        
        # Select a category to see its threads - use session state to remember last selection
        category_key = f"last_category_id_{persona_id}"
        if category_key not in st.session_state:
            st.session_state[category_key] = categories['category_id'].iloc[0] if not categories.empty else None
            
        category_id = st.selectbox(
            "Select Question Category",
            options=categories['category_id'].tolist(),
            format_func=lambda x: categories.loc[categories['category_id'] == x, 'name'].iloc[0],
            index=categories['category_id'].tolist().index(st.session_state[category_key]) if st.session_state[category_key] in categories['category_id'].values else 0
        )
        st.session_state[category_key] = category_id
        
        category_name = categories.loc[categories['category_id'] == category_id, 'name'].iloc[0]
        st.subheader(f"Threads for: {category_name}")
        
        # Form for adding a new thread
        with st.expander("Add New Thread"):
            with st.form("add_thread_form"):
                name = st.text_input("Thread Name")
                author = st.text_input("Created By (optional)")
                description = st.text_area("Description (optional)", height=100)
                submit_button = st.form_submit_button("Add Thread")
                
                if submit_button and name:
                    try:
                        # Pass created_by parameter
                        ThreadManager.create(category_id, name, description, author)
                        st.success(f"Added thread: {name}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding thread: {str(e)}")
        
        # Display and manage existing threads
        threads = ThreadManager.get_by_category(category_id)
        if not threads.empty:
            for _, row in threads.iterrows():
                with st.expander(f"{row['name']}"):
                    # Display thread details
                    st.write(f"**Description:** {row['description']}")
                    
                    # Show creator information if available
                    if 'created_by' in row and row['created_by']:
                        st.write(f"**Created By:** {row['created_by']}")
                    st.write(f"**Created:** {row['created_at']}")
                    
                    # Show updater information if available
                    if 'updated_by' in row and row['updated_by']:
                        st.write(f"**Updated By:** {row['updated_by']}")
                    st.write(f"**Updated:** {row['updated_at']}")
                    
                    # Edit form
                    form_key = f"edit_thread_{row['thread_id']}"
                    with st.form(form_key):
                        edit_name = st.text_input("Name", value=row['name'])
                        edit_author = st.text_input("Updated By (optional)")
                        edit_desc = st.text_area("Description (optional)", value=row['description'], height=100)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            update_button = st.form_submit_button("Update")
                        with col2:
                            delete_button = st.form_submit_button("Delete")
                    
                    if update_button and edit_name:
                        try:
                            # Pass updated_by parameter
                            ThreadManager.update(row['thread_id'], edit_name, edit_desc, edit_author)
                            st.success("Updated successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error updating thread: {str(e)}")
                    
                    if delete_button:
                        try:
                            ThreadManager.delete(row['thread_id'])
                            st.success("Deleted successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error deleting thread: {str(e)}")
        else:
            st.info(f"No threads have been added for {category_name} yet.")
    except Exception as e:
        st.error(f"Error on threads page: {str(e)}")

def question_page():
    st.header("Multi-Turn Question Thread")
    
    try:
        # Navigation selections for hierarchy
        personas = PersonaManager.get_all()
        if personas.empty:
            st.warning("Please add an AI Persona first.")
            return
        
        # Select a persona - use session state to remember last selection
        if 'last_persona_id' not in st.session_state:
            st.session_state.last_persona_id = personas['persona_id'].iloc[0] if not personas.empty else None
            
        persona_id = st.selectbox(
            "Select AI Persona",
            options=personas['persona_id'].tolist(),
            format_func=lambda x: personas.loc[personas['persona_id'] == x, 'name'].iloc[0],
            key="question_persona_select",
            index=personas['persona_id'].tolist().index(st.session_state.last_persona_id) if st.session_state.last_persona_id in personas['persona_id'].values else 0
        )
        st.session_state.last_persona_id = persona_id
        
        # Get categories for the selected persona
        categories = CategoryManager.get_by_persona(persona_id)
        if categories.empty:
            st.warning(f"Please add Categories for the selected persona first.")
            return
        
        # Select a category - use session state to remember last selection
        category_key = f"last_category_id_{persona_id}"
        if category_key not in st.session_state:
            st.session_state[category_key] = categories['category_id'].iloc[0] if not categories.empty else None
            
        category_id = st.selectbox(
            "Select Question Category",
            options=categories['category_id'].tolist(),
            format_func=lambda x: categories.loc[categories['category_id'] == x, 'name'].iloc[0],
            key="question_category_select",
            index=categories['category_id'].tolist().index(st.session_state[category_key]) if st.session_state[category_key] in categories['category_id'].values else 0
        )
        st.session_state[category_key] = category_id
        
        # Get threads for the selected category
        threads = ThreadManager.get_by_category(category_id)
        if threads.empty:
            st.warning(f"Please add Threads for the selected category first.")
            return
        
        # Select a thread - use session state to remember last selection
        thread_key = f"last_thread_id_{category_id}"
        if thread_key not in st.session_state:
            st.session_state[thread_key] = threads['thread_id'].iloc[0] if not threads.empty else None
            
        thread_id = st.selectbox(
            "Select Question Thread",
            options=threads['thread_id'].tolist(),
            format_func=lambda x: threads.loc[threads['thread_id'] == x, 'name'].iloc[0],
            key="question_thread_select",
            index=threads['thread_id'].tolist().index(st.session_state[thread_key]) if st.session_state[thread_key] in threads['thread_id'].values else 0
        )
        st.session_state[thread_key] = thread_id
        
        thread_name = threads.loc[threads['thread_id'] == thread_id, 'name'].iloc[0]
        st.subheader(f"Questions for thread: {thread_name}")
        
        # Form for adding a new question
        with st.expander("Add New Question"):
            with st.form("add_question_form"):
                content = st.text_area("Question Content")
                author = st.text_input("Created By (optional)")
                reference_links = st.text_area("Reference Links (optional)", 
                                          help="Add links to files, images, or other resources that this question refers to",
                                          height=100)
                
                questions = QuestionManager.get_by_thread(thread_id)
                max_seq = 1 if questions.empty else questions['sequence_number'].max() + 1
                
                sequence = st.number_input("Sequence Number", 
                                          min_value=1, 
                                          max_value=int(max_seq),
                                          value=int(max_seq))
                
                submit_button = st.form_submit_button("Add Question")
                
                if submit_button and content:
                    try:
                        # Pass created_by parameter
                        QuestionManager.create(thread_id, content, reference_links, author, sequence)
                        st.success("Added question successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding question: {str(e)}")
        
        # Display and manage existing questions
        questions = QuestionManager.get_by_thread(thread_id)
        if not questions.empty:
            st.write("### Question Sequence")
            
            # Show reordering options
            reorder_col1, reorder_col2 = st.columns([3, 1])
            with reorder_col1:
                st.write("You can change the sequence of questions by updating their sequence numbers.")
            with reorder_col2:
                if st.button("Reorder Questions"):
                    try:
                        QuestionManager.reorder(thread_id)
                        st.success("Questions reordered successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error reordering questions: {str(e)}")
            
            for i, (_, row) in enumerate(questions.iterrows(), 1):
                with st.expander(f"Q{row['sequence_number']}: {row['content'][:100]}..."):
                    # Display question details
                    st.write(f"**Full Question:** {row['content']}")
                    if 'reference_links' in row and row['reference_links']:
                        st.write(f"**Reference Links:** {row['reference_links']}")
                    st.write(f"**Sequence:** {row['sequence_number']}")
                    
                    # Show creator information if available
                    if 'created_by' in row and row['created_by']:
                        st.write(f"**Created By:** {row['created_by']}")
                    st.write(f"**Created:** {row['created_at']}")
                    
                    # Show updater information if available
                    if 'updated_by' in row and row['updated_by']:
                        st.write(f"**Updated By:** {row['updated_by']}")
                    st.write(f"**Updated:** {row['updated_at']}")
                    
                    # Edit form
                    form_key = f"edit_question_{row['question_id']}"
                    with st.form(form_key):
                        edit_content = st.text_area("Content", value=row['content'])
                        edit_author = st.text_input("Updated By (optional)")
                        edit_reference_links = st.text_area("Reference Links (optional)", 
                                                      value=row.get('reference_links', ''),
                                                      help="Add links to files, images, or other resources that this question refers to",
                                                      height=100)
                        edit_seq = st.number_input("Sequence", 
                                                  min_value=1,
                                                  value=int(row['sequence_number']))
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            update_button = st.form_submit_button("Update")
                        with col2:
                            delete_button = st.form_submit_button("Delete")
                    
                    if update_button and edit_content:
                        try:
                            # Pass updated_by parameter
                            QuestionManager.update(row['question_id'], edit_content, edit_reference_links, edit_author, edit_seq)
                            QuestionManager.reorder(thread_id)  # Ensure proper ordering
                            st.success("Updated successfully!")
                            # Clear the form after successful update
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error updating question: {str(e)}")
                    
                    if delete_button:
                        try:
                            QuestionManager.delete(row['question_id'])
                            st.success("Deleted successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error deleting question: {str(e)}")
                    
                    # Show answers for this question
                    answers = AnswerManager.get_by_question(row['question_id'])
                    st.write(f"**This question has {len(answers)} answers.**")
                    if not answers.empty:
                        for ans_idx, ans_row in answers.iterrows():
                            content_length = len(str(ans_row['content'])) if ans_row['content'] else 0
                            ans_author = f" by {ans_row['created_by']}" if 'created_by' in ans_row and ans_row['created_by'] else ""
                            st.write(f"- Answer {ans_idx+1}: \"{'AI' if ans_row['is_ai_generated'] else 'Human'} Response\"{ans_author} "
                                    f"({content_length} chars)")
        else:
            st.info(f"No questions have been added for this thread yet.")
    except Exception as e:
        st.error(f"Error on questions page: {str(e)}")

def answer_page():
    st.header("AI/Human Generated Answers")
    
    try:
        # Navigation selections for hierarchy
        personas = PersonaManager.get_all()
        if personas.empty:
            st.warning("Please add an AI Persona first.")
            return
        
        # Select a persona - use session state to remember last selection
        if 'last_persona_id' not in st.session_state:
            st.session_state.last_persona_id = personas['persona_id'].iloc[0] if not personas.empty else None
            
        persona_id = st.selectbox(
            "Select AI Persona",
            options=personas['persona_id'].tolist(),
            format_func=lambda x: personas.loc[personas['persona_id'] == x, 'name'].iloc[0],
            key="answer_persona_select",
            index=personas['persona_id'].tolist().index(st.session_state.last_persona_id) if st.session_state.last_persona_id in personas['persona_id'].values else 0
        )
        st.session_state.last_persona_id = persona_id
        
        # Get categories for the selected persona
        categories = CategoryManager.get_by_persona(persona_id)
        if categories.empty:
            st.warning(f"Please add Categories for the selected persona first.")
            return
        
        # Select a category - use session state to remember last selection
        category_key = f"last_category_id_{persona_id}"
        if category_key not in st.session_state:
            st.session_state[category_key] = categories['category_id'].iloc[0] if not categories.empty else None
            
        category_id = st.selectbox(
            "Select Question Category",
            options=categories['category_id'].tolist(),
            format_func=lambda x: categories.loc[categories['category_id'] == x, 'name'].iloc[0],
            key="answer_category_select",
            index=categories['category_id'].tolist().index(st.session_state[category_key]) if st.session_state[category_key] in categories['category_id'].values else 0
        )
        st.session_state[category_key] = category_id
        
        # Get threads for the selected category
        threads = ThreadManager.get_by_category(category_id)
        if threads.empty:
            st.warning(f"Please add Threads for the selected category first.")
            return
        
        # Select a thread - use session state to remember last selection
        thread_key = f"last_thread_id_{category_id}"
        if thread_key not in st.session_state:
            st.session_state[thread_key] = threads['thread_id'].iloc[0] if not threads.empty else None
            
        thread_id = st.selectbox(
            "Select Question Thread",
            options=threads['thread_id'].tolist(),
            format_func=lambda x: threads.loc[threads['thread_id'] == x, 'name'].iloc[0],
            key="answer_thread_select",
            index=threads['thread_id'].tolist().index(st.session_state[thread_key]) if st.session_state[thread_key] in threads['thread_id'].values else 0
        )
        st.session_state[thread_key] = thread_id
        
        # Get questions for the selected thread
        questions = QuestionManager.get_by_thread(thread_id)
        if questions.empty:
            st.warning(f"Please add Questions for the selected thread first.")
            return
        
        # Select a question - use session state to remember last selection
        question_key = f"last_question_id_{thread_id}"
        if question_key not in st.session_state:
            st.session_state[question_key] = questions['question_id'].iloc[0] if not questions.empty else None
            
        question_id = st.selectbox(
            "Select Question",
            options=questions['question_id'].tolist(),
            format_func=lambda x: f"Q{questions.loc[questions['question_id'] == x, 'sequence_number'].iloc[0]}: {questions.loc[questions['question_id'] == x, 'content'].iloc[0][:100]}...",
            key="answer_question_select",
            index=questions['question_id'].tolist().index(st.session_state[question_key]) if st.session_state[question_key] in questions['question_id'].values else 0
        )
        st.session_state[question_key] = question_id
        
        question_content = questions.loc[questions['question_id'] == question_id, 'content'].iloc[0]
        question_seq = questions.loc[questions['question_id'] == question_id, 'sequence_number'].iloc[0]
        
        st.subheader(f"Answers for Question {question_seq}")
        st.write(f"**Question:** {question_content}")
        
        # Form for adding a new answer
        with st.expander("Add New Answer"):
            with st.form("add_answer_form"):
                content = st.text_area("Answer Content")
                author = st.text_input("Created By (optional)")
                is_ai = st.checkbox("Is AI Generated", value=True)
                metadata = st.text_area("Metadata (optional)", height=100)
                
                submit_button = st.form_submit_button("Add Answer")
                
                if submit_button and content:
                    try:
                        # Pass created_by parameter
                        AnswerManager.create(question_id, content, is_ai, metadata, author)
                        st.success("Added answer successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding answer: {str(e)}")
        
        # Display and manage existing answers
        answers = AnswerManager.get_by_question(question_id)
        if not answers.empty:
            for i, (_, row) in enumerate(answers.iterrows(), 1):
                source_type = "AI Generated" if row['is_ai_generated'] else "Human Generated"
                with st.expander(f"Answer {i} ({source_type})"):
                    # Display answer details
                    st.write(f"**Content:** {row['content']}")
                    st.write(f"**Source:** {'AI' if row['is_ai_generated'] else 'Human'}")
                    if row['metadata']:
                        st.write(f"**Metadata:** {row['metadata']}")
                    
                    # Show creator information if available
                    if 'created_by' in row and row['created_by']:
                        st.write(f"**Created By:** {row['created_by']}")
                    st.write(f"**Created:** {row['created_at']}")
                    
                    # Show updater information if available
                    if 'updated_by' in row and row['updated_by']:
                        st.write(f"**Updated By:** {row['updated_by']}")
                    st.write(f"**Updated:** {row['updated_at']}")
                    
                    # Edit form
                    form_key = f"edit_answer_{row['answer_id']}"
                    with st.form(form_key):
                        edit_content = st.text_area("Content", value=row['content'])
                        edit_author = st.text_input("Updated By (optional)")
                        edit_is_ai = st.checkbox("Is AI Generated", value=bool(row['is_ai_generated']))
                        edit_metadata = st.text_area("Metadata (optional)", value=row['metadata'] if row['metadata'] else "", height=100)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            update_button = st.form_submit_button("Update")
                        with col2:
                            delete_button = st.form_submit_button("Delete")
                    
                    if update_button and edit_content:
                        try:
                            # Pass updated_by parameter
                            AnswerManager.update(row['answer_id'], edit_content, edit_is_ai, edit_metadata, edit_author)
                            st.success("Updated successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error updating answer: {str(e)}")
                    
                    if delete_button:
                        try:
                            AnswerManager.delete(row['answer_id'])
                            st.success("Deleted successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error deleting answer: {str(e)}")
                    
                    # Show evaluations for this answer
                    evaluations = EvaluationManager.get_by_answer(row['answer_id'])
                    st.write(f"**This answer has {len(evaluations)} evaluations.**")
                    if not evaluations.empty:
                        for eval_idx, eval_row in evaluations.iterrows():
                            evaluator_info = f" by {eval_row['evaluator']}" if eval_row['evaluator'] else ""
                            st.write(f"- {eval_row['dimension']}: Score {eval_row['score']}{evaluator_info}")
        else:
            st.info(f"No answers have been added for this question yet.")
    except Exception as e:
        st.error(f"Error on answers page: {str(e)}")

def evaluation_page():
    st.header("Multi-Dimensional Evaluation")
    
    try:
        # Navigation selections for hierarchy
        personas = PersonaManager.get_all()
        if personas.empty:
            st.warning("Please add an AI Persona first.")
            return
        
        # Select a persona - use session state to remember last selection
        if 'last_persona_id' not in st.session_state:
            st.session_state.last_persona_id = personas['persona_id'].iloc[0] if not personas.empty else None
            
        persona_id = st.selectbox(
            "Select AI Persona",
            options=personas['persona_id'].tolist(),
            format_func=lambda x: personas.loc[personas['persona_id'] == x, 'name'].iloc[0],
            key="eval_persona_select",
            index=personas['persona_id'].tolist().index(st.session_state.last_persona_id) if st.session_state.last_persona_id in personas['persona_id'].values else 0
        )
        st.session_state.last_persona_id = persona_id
        
        # Get categories for the selected persona
        categories = CategoryManager.get_by_persona(persona_id)
        if categories.empty:
            st.warning(f"Please add Categories for the selected persona first.")
            return
        
        # Select a category - use session state to remember last selection
        category_key = f"last_category_id_{persona_id}"
        if category_key not in st.session_state:
            st.session_state[category_key] = categories['category_id'].iloc[0] if not categories.empty else None
            
        category_id = st.selectbox(
            "Select Question Category",
            options=categories['category_id'].tolist(),
            format_func=lambda x: categories.loc[categories['category_id'] == x, 'name'].iloc[0],
            key="eval_category_select",
            index=categories['category_id'].tolist().index(st.session_state[category_key]) if st.session_state[category_key] in categories['category_id'].values else 0
        )
        st.session_state[category_key] = category_id
        
        # Get threads for the selected category
        threads = ThreadManager.get_by_category(category_id)
        if threads.empty:
            st.warning(f"Please add Threads for the selected category first.")
            return
        
        # Select a thread - use session state to remember last selection
        thread_key = f"last_thread_id_{category_id}"
        if thread_key not in st.session_state:
            st.session_state[thread_key] = threads['thread_id'].iloc[0] if not threads.empty else None
            
        thread_id = st.selectbox(
            "Select Question Thread",
            options=threads['thread_id'].tolist(),
            format_func=lambda x: threads.loc[threads['thread_id'] == x, 'name'].iloc[0],
            key="eval_thread_select",
            index=threads['thread_id'].tolist().index(st.session_state[thread_key]) if st.session_state[thread_key] in threads['thread_id'].values else 0
        )
        st.session_state[thread_key] = thread_id
        
        # Get questions for the selected thread
        questions = QuestionManager.get_by_thread(thread_id)
        if questions.empty:
            st.warning(f"Please add Questions for the selected thread first.")
            return
        
        # Select a question - use session state to remember last selection
        question_key = f"last_question_id_{thread_id}"
        if question_key not in st.session_state:
            st.session_state[question_key] = questions['question_id'].iloc[0] if not questions.empty else None
            
        question_id = st.selectbox(
            "Select Question",
            options=questions['question_id'].tolist(),
            format_func=lambda x: f"Q{questions.loc[questions['question_id'] == x, 'sequence_number'].iloc[0]}: {questions.loc[questions['question_id'] == x, 'content'].iloc[0][:100]}...",
            key="eval_question_select",
            index=questions['question_id'].tolist().index(st.session_state[question_key]) if st.session_state[question_key] in questions['question_id'].values else 0
        )
        st.session_state[question_key] = question_id
        
        # Get answers for the selected question
        answers = AnswerManager.get_by_question(question_id)
        if answers.empty:
            st.warning(f"Please add Answers for the selected question first.")
            return
        
        # Select an answer - use session state to remember last selection
        answer_key = f"last_answer_id_{question_id}"
        if answer_key not in st.session_state:
            st.session_state[answer_key] = answers['answer_id'].iloc[0] if not answers.empty else None
            
        answer_id = st.selectbox(
            "Select Answer",
            options=answers['answer_id'].tolist(),
            format_func=lambda x: f"Answer {answers.index[answers['answer_id'] == x][0] + 1} ({'AI' if answers.loc[answers['answer_id'] == x, 'is_ai_generated'].iloc[0] else 'Human'})",
            key="eval_answer_select",
            index=answers['answer_id'].tolist().index(st.session_state[answer_key]) if st.session_state[answer_key] in answers['answer_id'].values else 0
        )
        st.session_state[answer_key] = answer_id
        
        answer_content = answers.loc[answers['answer_id'] == answer_id, 'content'].iloc[0]
        answer_source = "AI Generated" if answers.loc[answers['answer_id'] == answer_id, 'is_ai_generated'].iloc[0] else "Human Generated"
        
        st.subheader(f"Evaluations for {answer_source} Answer")
        st.write("**Answer Content:**")
        st.text_area("Answer", value=answer_content, height=150, disabled=True)
        
        # Form for adding a new evaluation
        with st.expander("Add New Evaluation"):
            with st.form("add_evaluation_form"):
                dimension = st.text_input("Evaluation Dimension (e.g., Accuracy, Clarity)")
                author = st.text_input("Created By (optional)")
                score = st.slider("Score", min_value=0.0, max_value=10.0, value=5.0, step=1.0)
                comments = st.text_area("Comments/Feedback (optional)", height=100)
                evaluator = st.text_input("Evaluator Name (optional)")
                
                submit_button = st.form_submit_button("Add Evaluation")
                
                if submit_button and dimension:
                    try:
                        # Pass created_by parameter
                        EvaluationManager.create(answer_id, dimension, score, comments, evaluator, author)
                        st.success(f"Added evaluation for dimension: {dimension}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding evaluation: {str(e)}")
        
        # Display and manage existing evaluations
        evaluations = EvaluationManager.get_by_answer(answer_id)
        if not evaluations.empty:
            # Calculate and show average score
            avg_score = evaluations['score'].mean()
            st.metric("Average Evaluation Score", f"{avg_score:.1f}/10.0")
            
            for _, row in evaluations.iterrows():
                with st.expander(f"{row['dimension']} - Score: {row['score']}/10.0"):
                    # Display evaluation details
                    st.write(f"**Dimension:** {row['dimension']}")
                    st.write(f"**Score:** {row['score']}/10.0")
                    if row['comments']:
                        st.write(f"**Comments:** {row['comments']}")
                    if row['evaluator']:
                        st.write(f"**Evaluator:** {row['evaluator']}")
                    
                    # Show creator information if available
                    if 'created_by' in row and row['created_by']:
                        st.write(f"**Created By:** {row['created_by']}")
                    st.write(f"**Created:** {row['created_at']}")
                    
                    # Show updater information if available
                    if 'updated_by' in row and row['updated_by']:
                        st.write(f"**Updated By:** {row['updated_by']}")
                    st.write(f"**Updated:** {row['updated_at']}")
                    
                    # Edit form
                    form_key = f"edit_eval_{row['evaluation_id']}"
                    with st.form(form_key):
                        edit_dimension = st.text_input("Dimension", value=row['dimension'])
                        edit_author = st.text_input("Updated By (optional)")
                        edit_score = st.slider("Score", 
                                              min_value=0.0, 
                                              max_value=10.0, 
                                              value=float(row['score']), 
                                              step=1.0)
                        edit_comments = st.text_area("Comments (optional)", value=row['comments'] if row['comments'] else "", height=100)
                        edit_evaluator = st.text_input("Evaluator (optional)", value=row['evaluator'] if row['evaluator'] else "")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            update_button = st.form_submit_button("Update")
                        with col2:
                            delete_button = st.form_submit_button("Delete")
                    
                    if update_button:
                        try:
                            # Pass updated_by parameter
                            EvaluationManager.update(
                                row['evaluation_id'], 
                                edit_dimension, 
                                edit_score, 
                                edit_comments, 
                                edit_evaluator,
                                edit_author
                            )
                            st.success("Updated successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error updating evaluation: {str(e)}")
                    
                    if delete_button:
                        try:
                            EvaluationManager.delete(row['evaluation_id'])
                            st.success("Deleted successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error deleting evaluation: {str(e)}")
        else:
            st.info("No evaluations have been added for this answer yet.")
            
            # Suggest common dimensions
            st.write("### Suggested Evaluation Dimensions")
            st.write("Here are some common dimensions you might want to evaluate:")
            dimensions = [
                "Technical Accuracy", 
                "Reasoning Quality", 
                "Clarity of Explanation", 
                "Completeness",
                "Creativity",
                "Problem-Solving Approach",
                "Code Quality (if applicable)"
            ]
            for dim in dimensions:
                st.write(f"- {dim}")
    except Exception as e:
        st.error(f"Error on evaluation page: {str(e)}")

# Main function
def main():
    st.title("AI X Engineer Eval Bank")
    
    # Global variables for credentials
    global SUPABASE_URL, SUPABASE_KEY
    
    # Check session state
    if 'supabase_url' in st.session_state and 'supabase_key' in st.session_state:
        SUPABASE_URL = st.session_state.supabase_url
        SUPABASE_KEY = st.session_state.supabase_key
    
    # No credentials available
    if not SUPABASE_URL or not SUPABASE_KEY:
        st.sidebar.markdown("### Configure credentials")
        
        # Credential form
        st.header("Supabase Database Setup")
        
        # Form for inputting credentials
        with st.form("supabase_credentials_form"):
            url = st.text_input("Supabase URL", "https://your-project-id.supabase.co")
            key = st.text_input("Supabase anon/public Key", type="password")
            submit = st.form_submit_button("Connect to Supabase")
            
            if submit and url and key:
                st.session_state.supabase_url = url
                st.session_state.supabase_key = key
                SUPABASE_URL = url
                SUPABASE_KEY = key
                st.success("Credentials saved")
                st.rerun()
        
        # SQL setup info
        st.header("Database Setup")
        st.markdown("SQL script for table creation will appear here after connecting.")
        return
    
    # Credentials found
    st.sidebar.success("✅ Connected to database")
    
    # Reset credentials option
    if 'supabase_url' in st.session_state:
        if st.sidebar.button("Reset Credentials"):
            del st.session_state.supabase_url
            del st.session_state.supabase_key
            st.rerun()
    
    # Database setup
    if not initialize_database():
        st.warning("Set up database tables")
        st.header("Database Setup")
        st.markdown("Run this SQL in your Supabase SQL Editor:")
        st.code(get_table_creation_sql(), language="sql")
        return
    
    # Navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Select a page",
        ["AI Personas", "Question Categories", "Question Threads", 
         "Questions", "Answers", "Evaluations"]
    )
    
    if page == "AI Personas":
        persona_page()
    elif page == "Question Categories":
        category_page()
    elif page == "Question Threads":
        thread_page()
    elif page == "Questions":
        question_page()
    elif page == "Answers":
        answer_page()
    elif page == "Evaluations":
        evaluation_page()

if __name__ == "__main__":
    main()
