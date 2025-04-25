def evaluation_page():
    st.header("Multi-Dimensional Evaluation")
    
    # Define predefined evaluation dimensions
    PREDEFINED_DIMENSIONS = [
        "Accuracy/Correctness",
        "Relevance",
        "Completeness",
        "Reasoning",
        "Hallucination",
        "Verbose",
        "Additional Comments"
    ]
    
    DIMENSION_DESCRIPTIONS = {
        "Accuracy/Correctness": "Is the answer factually correct?",
        "Relevance": "Does the answer address the question?",
        "Completeness": "Does the answer fully address all aspects of the question?",
        "Reasoning": "Does the answer show clear, logical thinking—not just guesswork?",
        "Hallucination": "Is the model inventing facts or misrepresenting things? Is there irrelevant stuff in the answer?",
        "Verbose": "Is the answer too long or bloated? Could it be said simpler?",
        "Additional Comments": "Anything else worth pointing out? (Tone, clarity, examples, etc.)"
    }
    
    # Function to check if all dimensions have been evaluated
    def get_missing_dimensions(answer_id):
        existing_evals = EvaluationManager.get_by_answer(answer_id)
        if existing_evals.empty:
            return PREDEFINED_DIMENSIONS
        existing_dimensions = existing_evals['dimension'].values
        return [dim for dim in PREDEFINED_DIMENSIONS if dim not in existing_dimensions]
    
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
        
        # Get existing evaluations to check which dimensions have already been evaluated
        existing_evals = EvaluationManager.get_by_answer(answer_id)
        existing_dimensions = existing_evals['dimension'].tolist() if not existing_evals.empty else []
        
        # Form for adding/editing all evaluations at once
        with st.expander("Add or Edit Evaluations", expanded=True):
            with st.form("all_evaluations_form"):
                author = st.text_input("Evaluator Name")
                created_by = st.text_input("Created By (optional)")
                
                # Get existing evaluations to pre-fill form
                existing_evals_df = EvaluationManager.get_by_answer(answer_id)
                existing_evals = {}
                if not existing_evals_df.empty:
                    for _, row in existing_evals_df.iterrows():
                        existing_evals[row['dimension']] = {
                            'id': row['evaluation_id'],
                            'score': row['score'],
                            'comments': row['comments'] if 'comments' in row and row['comments'] else ""
                        }
                
                # Create input fields for each dimension without individual forms
                st.write("### Evaluation Dimensions")
                
                # Dictionary to store all the input values
                dimension_inputs = {}
                
                # Create input fields for each dimension in a more compact layout
                for dimension in PREDEFINED_DIMENSIONS:
                    # For regular dimensions, show dimension and slider on same line
                    if dimension != "Additional Comments":
                        col1, col2 = st.columns([3, 2])
                        with col1:
                            # Title and description on same line
                            st.markdown(f"**{dimension}** - {DIMENSION_DESCRIPTIONS[dimension]}")
                        with col2:
                            # Pre-fill if evaluation exists
                            default_score = existing_evals.get(dimension, {}).get('score', 5.0)
                            score = st.slider("", min_value=1.0, max_value=10.0, 
                                          value=float(default_score), step=1.0,
                                          key=f"score_{dimension}")
                            dimension_inputs[dimension] = {
                                'score': score,
                                'comments': ""  # No comments for regular dimensions
                            }
                    else:
                        # Additional Comments gets its own section
                        st.markdown(f"**{dimension}** - {DIMENSION_DESCRIPTIONS[dimension]}")
                        comments = st.text_area("", height=100, 
                                            value=existing_evals.get(dimension, {}).get('comments', ""),
                                            key=f"comments_{dimension}")
                        dimension_inputs[dimension] = {
                            'score': 0,  # Default score, won't be displayed
                            'comments': comments
                        }
                    
                    # Add a thin separator between dimensions
                    if dimension != PREDEFINED_DIMENSIONS[-1]:  # Don't add after the last dimension
                        st.markdown("---")  # Thinner divider
                
                # Single submit button for all dimensions
                submit_button = st.form_submit_button("Save All Evaluations")
                
                # Handle submission of all dimensions at once
                if submit_button:
                    success_count = 0
                    error_count = 0
                    
                    for dimension, values in dimension_inputs.items():
                        try:
                            if dimension in existing_evals:
                                # Update existing evaluation
                                eval_id = existing_evals[dimension]['id']
                                EvaluationManager.update(
                                    eval_id, 
                                    None,  # Don't change dimension
                                    values['score'] if dimension != "Additional Comments" else None,  # Only update score for regular dimensions
                                    values['comments'] if dimension == "Additional Comments" else None,  # Only update comments for Additional Comments
                                    author,
                                    created_by
                                )
                            else:
                                # Create new evaluation
                                EvaluationManager.create(
                                    answer_id, 
                                    dimension, 
                                    values['score'] if dimension != "Additional Comments" else 0,  # Use 0 score for Additional Comments
                                    values['comments'] if dimension == "Additional Comments" else "",  # Only pass comments for Additional Comments
                                    author, 
                                    created_by
                                )
                            success_count += 1
                        except Exception as e:
                            error_count += 1
                            st.error(f"Error saving {dimension}: {str(e)}")
                    
                    if success_count > 0:
                        st.success(f"Successfully saved {success_count} evaluations")
                        if error_count == 0:
                            st.rerun()
        
                    # Display evaluation summary
        evaluations = EvaluationManager.get_by_answer(answer_id)
        if not evaluations.empty:
            # Calculate and show average score (excluding "Additional Comments")
            score_evals = evaluations[evaluations['dimension'] != "Additional Comments"]
            if not score_evals.empty:
                avg_score = score_evals['score'].mean()
                st.metric("Average Score", f"{avg_score:.1f}/10")
            
            # Sort evaluations to match the predefined order
            dimension_order = {dim: i for i, dim in enumerate(PREDEFINED_DIMENSIONS)}
            evaluations['order'] = evaluations['dimension'].map(lambda d: dimension_order.get(d, 999))
            evaluations = evaluations.sort_values('order')
            
            # Show a summary of completed evaluations
            st.write("### Evaluation Summary")
            
            # Create a table layout without excessive spacing
            cols = st.columns([4, 1])
            with cols[0]:
                st.write("**Dimension**")
            with cols[1]:
                st.write("**Score**")
            
            # Add a divider between header and content
            st.divider()
            
            for _, row in evaluations.iterrows():
                cols = st.columns([4, 1])
                with cols[0]:
                    # Bold dimension and description on same line to save space
                    st.markdown(f"**{row['dimension']}** - {DIMENSION_DESCRIPTIONS[row['dimension']]}")
                with cols[1]:
                    # Only show scores for dimensions other than "Additional Comments"
                    if row['dimension'] != "Additional Comments":
                        st.write(f"{row['score']:.1f}/10")
                
                # Only show comments for "Additional Comments"
                if row['dimension'] == "Additional Comments" and row['comments']:
                    st.write(f"{row['comments']}")
                
                # Add a small divider between items
                st.markdown("---")  # Thinner divider
                
            # Show evaluator information if available
            if 'evaluator' in evaluations.iloc[0] and evaluations.iloc[0]['evaluator']:
                st.write(f"**Evaluator:** {evaluations.iloc[0]['evaluator']}")
            
            # Show which dimensions are missing
            missing_dimensions = [dim for dim in PREDEFINED_DIMENSIONS if dim not in evaluations['dimension'].values]
            if missing_dimensions:
                st.warning(f"Missing evaluations for: {', '.join(missing_dimensions)}")
        else:
            st.info("No evaluations have been added for this answer yet.")
    except Exception as e:
        st.error(f"Error on evaluation page: {str(e)}")
