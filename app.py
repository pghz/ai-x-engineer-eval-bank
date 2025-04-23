import streamlit as st
import pandas as pd
import os
from datetime import datetime
import json
from supabase import create_client, Client

# Supabase config
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
except (KeyError, FileNotFoundError):
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")

try:
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except (KeyError, FileNotFoundError):
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# Get Supabase client
def get_supabase_client():
    if 'supabase_url' in st.session_state and 'supabase_key' in st.session_state:
        url = st.session_state.supabase_url
        key = st.session_state.supabase_key
    else:
        url = SUPABASE_URL
        key = SUPABASE_KEY
    
    if not url or not key:
        st.error("Configure credentials first")
        st.stop()
    
    try:
        supabase = create_client(url, key)
        return supabase
    except Exception as e:
        st.error(f"Connection failed: {str(e)}")
        st.stop()

# Check if tables exist
def initialize_database():
    try:
        supabase = get_supabase_client()
        response = supabase.table('ai_personas').select('*').limit(1).execute()
        st.sidebar.success("✅ Tables ready")
        return True
    except Exception as e:
        error_message = str(e)
        if "relation" in error_message and "does not exist" in error_message:
            st.sidebar.error("Tables not set up")
        else:
            st.sidebar.error(f"DB error: {error_message}")
        return False

# Function to return the SQL needed to create tables in Supabase
def get_table_creation_sql():
    return """
-- AI Personas table
CREATE TABLE IF NOT EXISTS ai_personas (
    persona_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Question Categories table
CREATE TABLE IF NOT EXISTS question_categories (
    category_id SERIAL PRIMARY KEY,
    persona_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (persona_id) REFERENCES ai_personas(persona_id) ON DELETE CASCADE
);

-- Question Threads table
CREATE TABLE IF NOT EXISTS question_threads (
    thread_id SERIAL PRIMARY KEY,
    category_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES question_categories(category_id) ON DELETE CASCADE
);

-- Questions table
CREATE TABLE IF NOT EXISTS questions (
    question_id SERIAL PRIMARY KEY,
    thread_id INTEGER NOT NULL,
    sequence_number INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
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
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
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
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (answer_id) REFERENCES answers(answer_id) ON DELETE CASCADE
);
"""

# CRUD operations for each table
class PersonaManager:
    @staticmethod
    def create(name, description=""):
        supabase = get_supabase_client()
        result = supabase.table('ai_personas').insert({
            "name": name,
            "description": description
        }).execute()
        
        if result.data:
            return result.data[0]['persona_id']
        return None
    
    @staticmethod
    def get_all():
        supabase = get_supabase_client()
        result = supabase.table('ai_personas').select('*').order('name').execute()
        return pd.DataFrame(result.data) if result.data else pd.DataFrame()
    
    @staticmethod
    def get_by_id(persona_id):
        supabase = get_supabase_client()
        result = supabase.table('ai_personas').select('*').eq('persona_id', persona_id).execute()
        return pd.DataFrame(result.data) if result.data else pd.DataFrame()
    
    @staticmethod
    def update(persona_id, name, description):
        supabase = get_supabase_client()
        supabase.table('ai_personas').update({
            "name": name,
            "description": description,
            "updated_at": datetime.now().isoformat()
        }).eq('persona_id', persona_id).execute()
    
    @staticmethod
    def delete(persona_id):
        supabase = get_supabase_client()
        supabase.table('ai_personas').delete().eq('persona_id', persona_id).execute()

class CategoryManager:
    @staticmethod
    def create(persona_id, name, description=""):
        supabase = get_supabase_client()
        result = supabase.table('question_categories').insert({
            "persona_id": persona_id,
            "name": name,
            "description": description
        }).execute()
        
        if result.data:
            return result.data[0]['category_id']
        return None
    
    @staticmethod
    def get_by_persona(persona_id):
        supabase = get_supabase_client()
        result = supabase.table('question_categories')\
            .select('*')\
            .eq('persona_id', persona_id)\
            .order('name')\
            .execute()
        return pd.DataFrame(result.data) if result.data else pd.DataFrame()
    
    @staticmethod
    def get_by_id(category_id):
        supabase = get_supabase_client()
        result = supabase.table('question_categories')\
            .select('*')\
            .eq('category_id', category_id)\
            .execute()
        return pd.DataFrame(result.data) if result.data else pd.DataFrame()
    
    @staticmethod
    def update(category_id, name, description):
        supabase = get_supabase_client()
        supabase.table('question_categories').update({
            "name": name,
            "description": description,
            "updated_at": datetime.now().isoformat()
        }).eq('category_id', category_id).execute()
    
    @staticmethod
    def delete(category_id):
        supabase = get_supabase_client()
        supabase.table('question_categories').delete().eq('category_id', category_id).execute()

class ThreadManager:
    @staticmethod
    def create(category_id, name, description=""):
        supabase = get_supabase_client()
        result = supabase.table('question_threads').insert({
            "category_id": category_id,
            "name": name,
            "description": description
        }).execute()
        
        if result.data:
            return result.data[0]['thread_id']
        return None
    
    @staticmethod
    def get_by_category(category_id):
        supabase = get_supabase_client()
        result = supabase.table('question_threads')\
            .select('*')\
            .eq('category_id', category_id)\
            .order('name')\
            .execute()
        return pd.DataFrame(result.data) if result.data else pd.DataFrame()
    
    @staticmethod
    def get_by_id(thread_id):
        supabase = get_supabase_client()
        result = supabase.table('question_threads')\
            .select('*')\
            .eq('thread_id', thread_id)\
            .execute()
        return pd.DataFrame(result.data) if result.data else pd.DataFrame()
    
    @staticmethod
    def update(thread_id, name, description):
        supabase = get_supabase_client()
        supabase.table('question_threads').update({
            "name": name,
            "description": description,
            "updated_at": datetime.now().isoformat()
        }).eq('thread_id', thread_id).execute()
    
    @staticmethod
    def delete(thread_id):
        supabase = get_supabase_client()
        supabase.table('question_threads').delete().eq('thread_id', thread_id).execute()

class QuestionManager:
    @staticmethod
    def create(thread_id, content, sequence_number=None):
        supabase = get_supabase_client()
        
        # If sequence_number not provided, find the next one
        if sequence_number is None:
            result = supabase.table('questions')\
                .select('sequence_number')\
                .eq('thread_id', thread_id)\
                .order('sequence_number', desc=True)\
                .limit(1)\
                .execute()
            
            sequence_number = 1
            if result.data:
                sequence_number = result.data[0]['sequence_number'] + 1
        
        result = supabase.table('questions').insert({
            "thread_id": thread_id,
            "sequence_number": sequence_number,
            "content": content
        }).execute()
        
        if result.data:
            return result.data[0]['question_id']
        return None
    
    @staticmethod
    def get_by_thread(thread_id):
        supabase = get_supabase_client()
        result = supabase.table('questions')\
            .select('*')\
            .eq('thread_id', thread_id)\
            .order('sequence_number')\
            .execute()
        return pd.DataFrame(result.data) if result.data else pd.DataFrame()
    
    @staticmethod
    def get_by_id(question_id):
        supabase = get_supabase_client()
        result = supabase.table('questions')\
            .select('*')\
            .eq('question_id', question_id)\
            .execute()
        return pd.DataFrame(result.data) if result.data else pd.DataFrame()
    
    @staticmethod
    def update(question_id, content, sequence_number=None):
        supabase = get_supabase_client()
        update_data = {
            "content": content,
            "updated_at": datetime.now().isoformat()
        }
        
        if sequence_number is not None:
            update_data["sequence_number"] = sequence_number
        
        supabase.table('questions')\
            .update(update_data)\
            .eq('question_id', question_id)\
            .execute()
    
    @staticmethod
    def delete(question_id):
        supabase = get_supabase_client()
        supabase.table('questions').delete().eq('question_id', question_id).execute()
    
    @staticmethod
    def reorder(thread_id):
        """Reindex sequence numbers to be consecutive integers starting from 1"""
        supabase = get_supabase_client()
        
        # Get all questions for this thread ordered by current sequence
        result = supabase.table('questions')\
            .select('question_id')\
            .eq('thread_id', thread_id)\
            .order('sequence_number')\
            .execute()
        
        if not result.data:
            return
        
        # Update sequence numbers to be consecutive
        for idx, row in enumerate(result.data, 1):
            supabase.table('questions')\
                .update({"sequence_number": idx})\
                .eq('question_id', row['question_id'])\
                .execute()

class AnswerManager:
    @staticmethod
    def create(question_id, content, is_ai_generated=True, metadata=""):
        supabase = get_supabase_client()
        result = supabase.table('answers').insert({
            "question_id": question_id,
            "is_ai_generated": is_ai_generated,
            "content": content,
            "metadata": metadata
        }).execute()
        
        if result.data:
            return result.data[0]['answer_id']
        return None
    
    @staticmethod
    def get_by_question(question_id):
        supabase = get_supabase_client()
        result = supabase.table('answers')\
            .select('*')\
            .eq('question_id', question_id)\
            .order('created_at')\
            .execute()
        return pd.DataFrame(result.data) if result.data else pd.DataFrame()
    
    @staticmethod
    def get_by_id(answer_id):
        supabase = get_supabase_client()
        result = supabase.table('answers')\
            .select('*')\
            .eq('answer_id', answer_id)\
            .execute()
        return pd.DataFrame(result.data) if result.data else pd.DataFrame()
    
    @staticmethod
    def update(answer_id, content, is_ai_generated=None, metadata=None):
        supabase = get_supabase_client()
        update_data = {
            "content": content,
            "updated_at": datetime.now().isoformat()
        }
        
        if is_ai_generated is not None:
            update_data["is_ai_generated"] = is_ai_generated
        
        if metadata is not None:
            update_data["metadata"] = metadata
        
        supabase.table('answers')\
            .update(update_data)\
            .eq('answer_id', answer_id)\
            .execute()
    
    @staticmethod
    def delete(answer_id):
        supabase = get_supabase_client()
        supabase.table('answers').delete().eq('answer_id', answer_id).execute()

class EvaluationManager:
    @staticmethod
    def create(answer_id, dimension, score, comments="", evaluator=""):
        supabase = get_supabase_client()
        result = supabase.table('evaluations').insert({
            "answer_id": answer_id,
            "dimension": dimension,
            "score": score,
            "comments": comments,
            "evaluator": evaluator
        }).execute()
        
        if result.data:
            return result.data[0]['evaluation_id']
        return None
    
    @staticmethod
    def get_by_answer(answer_id):
        supabase = get_supabase_client()
        result = supabase.table('evaluations')\
            .select('*')\
            .eq('answer_id', answer_id)\
            .order('dimension')\
            .execute()
        return pd.DataFrame(result.data) if result.data else pd.DataFrame()
    
    @staticmethod
    def get_dimensions_for_answer(answer_id):
        supabase = get_supabase_client()
        result = supabase.table('evaluations')\
            .select('dimension')\
            .eq('answer_id', answer_id)\
            .execute()
        return [row['dimension'] for row in result.data] if result.data else []
    
    @staticmethod
    def get_by_id(evaluation_id):
        supabase = get_supabase_client()
        result = supabase.table('evaluations')\
            .select('*')\
            .eq('evaluation_id', evaluation_id)\
            .execute()
        return pd.DataFrame(result.data) if result.data else pd.DataFrame()
    
    @staticmethod
    def update(evaluation_id, dimension=None, score=None, comments=None, evaluator=None):
        supabase = get_supabase_client()
        update_data = {"updated_at": datetime.now().isoformat()}
        
        if dimension is not None:
            update_data["dimension"] = dimension
        
        if score is not None:
            update_data["score"] = score
        
        if comments is not None:
            update_data["comments"] = comments
        
        if evaluator is not None:
            update_data["evaluator"] = evaluator
        
        supabase.table('evaluations')\
            .update(update_data)\
            .eq('evaluation_id', evaluation_id)\
            .execute()
    
    @staticmethod
    def delete(evaluation_id):
        supabase = get_supabase_client()
        supabase.table('evaluations').delete().eq('evaluation_id', evaluation_id).execute()

# Streamlit UI functions - these remain mostly the same as your original code
def persona_page():
    st.header("AI X-Engineer Personas")
    
    # Form for adding a new persona
    with st.expander("Add New Persona"):
        with st.form("add_persona_form"):
            name = st.text_input("Persona Name")
            description = st.text_area("Description")
            submit_button = st.form_submit_button("Add Persona")
            
            if submit_button and name:
                try:
                    PersonaManager.create(name, description)
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
                    # Display persona details
                    st.write(f"**Description:** {row['description']}")
                    st.write(f"**Created:** {row['created_at']}")
                    st.write(f"**Updated:** {row['updated_at']}")
                    
                    # Edit form
                    with st.form(f"edit_persona_{row['persona_id']}"):
                        edit_name = st.text_input("Name", value=row['name'])
                        edit_desc = st.text_area("Description", value=row['description'])
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            update_button = st.form_submit_button("Update")
                        with col2:
                            delete_button = st.form_submit_button("Delete")
                    
                    if update_button and edit_name:
                        try:
                            PersonaManager.update(row['persona_id'], edit_name, edit_desc)
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
        
        # Select a persona to see its categories
        persona_id = st.selectbox(
            "Select AI Persona",
            options=personas['persona_id'].tolist(),
            format_func=lambda x: personas.loc[personas['persona_id'] == x, 'name'].iloc[0]
        )
        
        persona_name = personas.loc[personas['persona_id'] == persona_id, 'name'].iloc[0]
        st.subheader(f"Categories for: {persona_name}")
        
        # Form for adding a new category
        with st.expander("Add New Category"):
            with st.form("add_category_form"):
                name = st.text_input("Category Name")
                description = st.text_area("Description")
                submit_button = st.form_submit_button("Add Category")
                
                if submit_button and name:
                    try:
                        CategoryManager.create(persona_id, name, description)
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
                    st.write(f"**Created:** {row['created_at']}")
                    st.write(f"**Updated:** {row['updated_at']}")
                    
                    # Edit form
                    with st.form(f"edit_category_{row['category_id']}"):
                        edit_name = st.text_input("Name", value=row['name'])
                        edit_desc = st.text_area("Description", value=row['description'])
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            update_button = st.form_submit_button("Update")
                        with col2:
                            delete_button = st.form_submit_button("Delete")
                    
                    if update_button and edit_name:
                        try:
                            CategoryManager.update(row['category_id'], edit_name, edit_desc)
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
        
        # Select a persona to see its categories
        persona_id = st.selectbox(
            "Select AI Persona",
            options=personas['persona_id'].tolist(),
            format_func=lambda x: personas.loc[personas['persona_id'] == x, 'name'].iloc[0]
        )
        
        # Get categories for the selected persona
        categories = CategoryManager.get_by_persona(persona_id)
        if categories.empty:
            st.warning(f"Please add Categories for the selected persona first.")
            return
        
        # Select a category to see its threads
        category_id = st.selectbox(
            "Select Question Category",
            options=categories['category_id'].tolist(),
            format_func=lambda x: categories.loc[categories['category_id'] == x, 'name'].iloc[0]
        )
        
        category_name = categories.loc[categories['category_id'] == category_id, 'name'].iloc[0]
        st.subheader(f"Threads for: {category_name}")
        
        # Form for adding a new thread
        with st.expander("Add New Thread"):
            with st.form("add_thread_form"):
                name = st.text_input("Thread Name")
                description = st.text_area("Description")
                submit_button = st.form_submit_button("Add Thread")
                
                if submit_button and name:
                    try:
                        ThreadManager.create(category_id, name, description)
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
                    st.write(f"**Created:** {row['created_at']}")
                    st.write(f"**Updated:** {row['updated_at']}")
                    
                    # Edit form
                    with st.form(f"edit_thread_{row['thread_id']}"):
                        edit_name = st.text_input("Name", value=row['name'])
                        edit_desc = st.text_area("Description", value=row['description'])
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            update_button = st.form_submit_button("Update")
                        with col2:
                            delete_button = st.form_submit_button("Delete")
                    
                    if update_button and edit_name:
                        try:
                            ThreadManager.update(row['thread_id'], edit_name, edit_desc)
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
        
        # Select a persona
        persona_id = st.selectbox(
            "Select AI Persona",
            options=personas['persona_id'].tolist(),
            format_func=lambda x: personas.loc[personas['persona_id'] == x, 'name'].iloc[0],
            key="question_persona_select"
        )
        
        # Get categories for the selected persona
        categories = CategoryManager.get_by_persona(persona_id)
        if categories.empty:
            st.warning(f"Please add Categories for the selected persona first.")
            return
        
        # Select a category
        category_id = st.selectbox(
            "Select Question Category",
            options=categories['category_id'].tolist(),
            format_func=lambda x: categories.loc[categories['category_id'] == x, 'name'].iloc[0],
            key="question_category_select"
        )
        
        # Get threads for the selected category
        threads = ThreadManager.get_by_category(category_id)
        if threads.empty:
            st.warning(f"Please add Threads for the selected category first.")
            return
        
        # Select a thread
        thread_id = st.selectbox(
            "Select Question Thread",
            options=threads['thread_id'].tolist(),
            format_func=lambda x: threads.loc[threads['thread_id'] == x, 'name'].iloc[0],
            key="question_thread_select"
        )
        
        thread_name = threads.loc[threads['thread_id'] == thread_id, 'name'].iloc[0]
        st.subheader(f"Questions for thread: {thread_name}")
        
        # Form for adding a new question
        with st.expander("Add New Question"):
            with st.form("add_question_form"):
                content = st.text_area("Question Content")
                
                questions = QuestionManager.get_by_thread(thread_id)
                max_seq = 1 if questions.empty else questions['sequence_number'].max() + 1
                
                sequence = st.number_input("Sequence Number", 
                                          min_value=1, 
                                          max_value=int(max_seq),
                                          value=int(max_seq))
                
                submit_button = st.form_submit_button("Add Question")
                
                if submit_button and content:
                    try:
                        QuestionManager.create(thread_id, content, sequence)
                        QuestionManager.reorder(thread_id)  # Ensure proper ordering
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
                with st.expander(f"Q{row['sequence_number']}: {row['content'][:50]}..."):
                    # Display question details
                    st.write(f"**Full Question:** {row['content']}")
                    st.write(f"**Sequence:** {row['sequence_number']}")
                    st.write(f"**Created:** {row['created_at']}")
                    st.write(f"**Updated:** {row['updated_at']}")
                    
                    # Edit form
                    with st.form(f"edit_question_{row['question_id']}"):
                        edit_content = st.text_area("Content", value=row['content'])
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
                            QuestionManager.update(row['question_id'], edit_content, edit_seq)
                            QuestionManager.reorder(thread_id)  # Ensure proper ordering
                            st.success("Updated successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error updating question: {str(e)}")
                    
                    if delete_button:
                        try:
                            QuestionManager.delete(row['question_id'])
                            QuestionManager.reorder(thread_id)  # Ensure proper ordering
                            st.success("Deleted successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error deleting question: {str(e)}")
                    
                    # Show answers for this question
                    answers = AnswerManager.get_by_question(row['question_id'])
                    st.write(f"**This question has {len(answers)} answers.**")
                    if not answers.empty:
                        for ans_idx, ans_row in answers.iterrows():
                            st.write(f"- Answer {ans_idx+1}: \"{'AI' if ans_row['is_ai_generated'] else 'Human'} Response\" "
                                    f"({len(ans_row['content'])[:30]} chars)")
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
        
        # Select a persona
        persona_id = st.selectbox(
            "Select AI Persona",
            options=personas['persona_id'].tolist(),
            format_func=lambda x: personas.loc[personas['persona_id'] == x, 'name'].iloc[0],
            key="answer_persona_select"
        )
        
        # Get categories for the selected persona
        categories = CategoryManager.get_by_persona(persona_id)
        if categories.empty:
            st.warning(f"Please add Categories for the selected persona first.")
            return
        
        # Select a category
        category_id = st.selectbox(
            "Select Question Category",
            options=categories['category_id'].tolist(),
            format_func=lambda x: categories.loc[categories['category_id'] == x, 'name'].iloc[0],
            key="answer_category_select"
        )
        
        # Get threads for the selected category
        threads = ThreadManager.get_by_category(category_id)
        if threads.empty:
            st.warning(f"Please add Threads for the selected category first.")
            return
        
        # Select a thread
        thread_id = st.selectbox(
            "Select Question Thread",
            options=threads['thread_id'].tolist(),
            format_func=lambda x: threads.loc[threads['thread_id'] == x, 'name'].iloc[0],
            key="answer_thread_select"
        )
        
        # Get questions for the selected thread
        questions = QuestionManager.get_by_thread(thread_id)
        if questions.empty:
            st.warning(f"Please add Questions for the selected thread first.")
            return
        
        # Select a question
        question_id = st.selectbox(
            "Select Question",
            options=questions['question_id'].tolist(),
            format_func=lambda x: f"Q{questions.loc[questions['question_id'] == x, 'sequence_number'].iloc[0]}: {questions.loc[questions['question_id'] == x, 'content'].iloc[0][:50]}...",
            key="answer_question_select"
        )
        
        question_content = questions.loc[questions['question_id'] == question_id, 'content'].iloc[0]
        question_seq = questions.loc[questions['question_id'] == question_id, 'sequence_number'].iloc[0]
        
        st.subheader(f"Answers for Question {question_seq}")
        st.write(f"**Question:** {question_content}")
        
        # Form for adding a new answer
        with st.expander("Add New Answer"):
            with st.form("add_answer_form"):
                content = st.text_area("Answer Content")
                is_ai = st.checkbox("Is AI Generated", value=True)
                metadata = st.text_area("Metadata (optional)")
                
                submit_button = st.form_submit_button("Add Answer")
                
                if submit_button and content:
                    try:
                        AnswerManager.create(question_id, content, is_ai, metadata)
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
                    st.write(f"**Metadata:** {row['metadata']}")
                    st.write(f"**Created:** {row['created_at']}")
                    st.write(f"**Updated:** {row['updated_at']}")
                    
                    # Edit form
                    with st.form(f"edit_answer_{row['answer_id']}"):
                        edit_content = st.text_area("Content", value=row['content'])
                        edit_is_ai = st.checkbox("Is AI Generated", value=bool(row['is_ai_generated']))
                        edit_metadata = st.text_area("Metadata", value=row['metadata'] if row['metadata'] else "")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            update_button = st.form_submit_button("Update")
                        with col2:
                            delete_button = st.form_submit_button("Delete")
                    
                    if update_button and edit_content:
                        try:
                            AnswerManager.update(row['answer_id'], edit_content, edit_is_ai, edit_metadata)
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
                            st.write(f"- {eval_row['dimension']}: Score {eval_row['score']}")
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
        
        # Select a persona
        persona_id = st.selectbox(
            "Select AI Persona",
            options=personas['persona_id'].tolist(),
            format_func=lambda x: personas.loc[personas['persona_id'] == x, 'name'].iloc[0],
            key="eval_persona_select"
        )
        
        # Get categories for the selected persona
        categories = CategoryManager.get_by_persona(persona_id)
        if categories.empty:
            st.warning(f"Please add Categories for the selected persona first.")
            return
        
        # Select a category
        category_id = st.selectbox(
            "Select Question Category",
            options=categories['category_id'].tolist(),
            format_func=lambda x: categories.loc[categories['category_id'] == x, 'name'].iloc[0],
            key="eval_category_select"
        )
        
        # Get threads for the selected category
        threads = ThreadManager.get_by_category(category_id)
        if threads.empty:
            st.warning(f"Please add Threads for the selected category first.")
            return
        
        # Select a thread
        thread_id = st.selectbox(
            "Select Question Thread",
            options=threads['thread_id'].tolist(),
            format_func=lambda x: threads.loc[threads['thread_id'] == x, 'name'].iloc[0],
            key="eval_thread_select"
        )
        
        # Get questions for the selected thread
        questions = QuestionManager.get_by_thread(thread_id)
        if questions.empty:
            st.warning(f"Please add Questions for the selected thread first.")
            return
        
        # Select a question
        question_id = st.selectbox(
            "Select Question",
            options=questions['question_id'].tolist(),
            format_func=lambda x: f"Q{questions.loc[questions['question_id'] == x, 'sequence_number'].iloc[0]}: {questions.loc[questions['question_id'] == x, 'content'].iloc[0][:50]}...",
            key="eval_question_select"
        )
        
        # Get answers for the selected question
        answers = AnswerManager.get_by_question(question_id)
        if answers.empty:
            st.warning(f"Please add Answers for the selected question first.")
            return
        
        # Select an answer
        answer_id = st.selectbox(
            "Select Answer",
            options=answers['answer_id'].tolist(),
            format_func=lambda x: f"Answer {answers.index[answers['answer_id'] == x][0] + 1} ({'AI' if answers.loc[answers['answer_id'] == x, 'is_ai_generated'].iloc[0] else 'Human'})",
            key="eval_answer_select"
        )
        
        answer_content = answers.loc[answers['answer_id'] == answer_id, 'content'].iloc[0]
        answer_source = "AI Generated" if answers.loc[answers['answer_id'] == answer_id, 'is_ai_generated'].iloc[0] else "Human Generated"
        
        st.subheader(f"Evaluations for {answer_source} Answer")
        st.write("**Answer Content:**")
        st.text_area("Answer", value=answer_content, height=150, disabled=True)
        
        # Form for adding a new evaluation
        with st.expander("Add New Evaluation"):
            with st.form("add_evaluation_form"):
                dimension = st.text_input("Evaluation Dimension (e.g., Accuracy, Clarity)")
                score = st.slider("Score", min_value=0.0, max_value=10.0, value=5.0, step=0.1)
                comments = st.text_area("Comments/Feedback")
                evaluator = st.text_input("Evaluator Name")
                
                submit_button = st.form_submit_button("Add Evaluation")
                
                if submit_button and dimension:
                    try:
                        EvaluationManager.create(answer_id, dimension, score, comments, evaluator)
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
                    st.write(f"**Comments:** {row['comments']}")
                    st.write(f"**Evaluator:** {row['evaluator']}")
                    st.write(f"**Created:** {row['created_at']}")
                    st.write(f"**Updated:** {row['updated_at']}")
                    
                    # Edit form
                    with st.form(f"edit_eval_{row['evaluation_id']}"):
                        edit_dimension = st.text_input("Dimension", value=row['dimension'])
                        edit_score = st.slider("Score", 
                                              min_value=0.0, 
                                              max_value=10.0, 
                                              value=float(row['score']), 
                                              step=0.1)
                        edit_comments = st.text_area("Comments", value=row['comments'] if row['comments'] else "")
                        edit_evaluator = st.text_input("Evaluator", value=row['evaluator'] if row['evaluator'] else "")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            update_button = st.form_submit_button("Update")
                        with col2:
                            delete_button = st.form_submit_button("Delete")
                    
                    if update_button:
                        try:
                            EvaluationManager.update(
                                row['evaluation_id'], 
                                edit_dimension, 
                                edit_score, 
                                edit_comments, 
                                edit_evaluator
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
        st.sidebar.title("Configure Credentials →")
        
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
