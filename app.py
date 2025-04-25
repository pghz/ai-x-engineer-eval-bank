class EvaluationManager:
    # Define the predefined dimensions as a class variable for reuse
    PREDEFINED_DIMENSIONS = [
        "Accuracy/Correctness",
        "Relevance",
        "Completeness",
        "Reasoning",
        "Hallucination",
        "Verbose",
        "Additional Comments"
    ]
    
    @staticmethod
    def create(answer_id, dimension, score, comments="", evaluator="", created_by=""):
        # Validate that the dimension is one of the predefined dimensions
        if dimension not in EvaluationManager.PREDEFINED_DIMENSIONS:
            st.error(f"Invalid dimension: {dimension}. Must be one of the predefined dimensions.")
            return None
            
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
    def get_missing_dimensions_for_answer(answer_id):
        # Get dimensions that have already been evaluated
        evaluated_dimensions = EvaluationManager.get_dimensions_for_answer(answer_id)
        # Return dimensions that haven't been evaluated yet
        return [dim for dim in EvaluationManager.PREDEFINED_DIMENSIONS if dim not in evaluated_dimensions]
    
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
            # Validate that the dimension is one of the predefined dimensions
            if dimension not in EvaluationManager.PREDEFINED_DIMENSIONS:
                st.error(f"Invalid dimension: {dimension}. Must be one of the predefined dimensions.")
                return False
            data["dimension"] = dimension
        
        if score is not None:
            data["score"] = score
        
        if comments is not None:
            data["comments"] = comments
        
        if evaluator is not None:
            data["evaluator"] = evaluator
        
        result = supabase_request("patch", "evaluations", 
                       params={"evaluation_id": f"eq.{evaluation_id}"}, 
                       data=data)
        return result is not None
    
    @staticmethod
    def delete(evaluation_id):
        result = supabase_request("delete", "evaluations", 
                       params={"evaluation_id": f"eq.{evaluation_id}"})
        return result is not None
