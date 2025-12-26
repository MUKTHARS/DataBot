import re
from typing import Any, Dict, List

class ResponseFormatter:
    """Formats responses with professional structure WITHOUT asterisks"""
    
    @staticmethod
    def format_structured_response(query: str, data: Any, query_used: str = None) -> str:
        """Format response with professional structure WITHOUT asterisks"""
        
        if not data or (isinstance(data, list) and len(data) == 0):
            return ResponseFormatter._format_no_data_response(query)
        
        if isinstance(data, list):
            return ResponseFormatter._format_list_response(data, query)
        
        if isinstance(data, dict):
            return ResponseFormatter._format_dict_response(data, query)
        
        return f"Result: {str(data)}"
    
    @staticmethod
    def _format_no_data_response(query: str) -> str:
        """Format response when no data is found"""
        response = f"""No Matching Data Found

Your query about {query} did not return any results. 

Possible reasons:
• The requested data doesn't exist in the database
• Your query criteria are too specific
• There might be a spelling or terminology issue

Suggestions:
1. Try broadening your search criteria
2. Check for alternative terminology
3. Verify if the data exists in the current database
4. Consider asking a more general question first"""
        
        return response
    
    @staticmethod
    def _format_list_response(data: List[Dict], query: str) -> str:
        """Format response for list data WITHOUT asterisks"""
        count = len(data)
        
        if count == 0:
            return ResponseFormatter._format_no_data_response(query)
        
        sample = data[0] if data else {}
        
        response_lines = [
            f"Query Analysis Complete",
            f"",
            f"Found {count} records matching your query about {query}.",
            f""
        ]
        
        # Add summary
        if count > 0 and isinstance(sample, dict):
            numeric_fields = []
            categorical_fields = []
            
            for key, value in sample.items():
                if isinstance(value, (int, float)):
                    numeric_fields.append(key)
                else:
                    categorical_fields.append(key)
            
            if numeric_fields:
                response_lines.append("Key Numerical Fields:")
                response_lines.append(f"• {', '.join(numeric_fields[:5])}")
                response_lines.append("")
            
            if categorical_fields:
                response_lines.append("Available Data Categories:")
                response_lines.append(f"• {', '.join(categorical_fields[:5])}")
                response_lines.append("")
        
        # Add sample data WITHOUT asterisks
        response_lines.append("Sample Data Preview:")
        
        for i, row in enumerate(data[:3]):
            response_lines.append(f"{i+1}. Row {i+1}:")
            for key, value in list(row.items())[:3]:
                response_lines.append(f"   • {key}: {str(value)[:50]}")
        
        if count > 3:
            response_lines.append(f"")
            response_lines.append(f"... and {count - 3} more records")
        
        response_lines.append(f"")
        response_lines.append("Next Analysis Steps:")
        response_lines.append("1. Drill down into specific records")
        response_lines.append("2. Request summary statistics")
        response_lines.append("3. Ask for trends over time")
        response.append("4. Compare different categories")
        
        return "\n".join(response_lines)
    
    @staticmethod
    def _format_dict_response(data: Dict, query: str) -> str:
        """Format response for dictionary data WITHOUT asterisks"""
        response_lines = [
            f"Analysis Results",
            f"",
            f"Analysis of {query} returned the following findings:",
            f""
        ]
        
        for key, value in data.items():
            formatted_key = key.replace('_', ' ').title()
            if isinstance(value, (int, float)):
                response_lines.append(f"• {formatted_key}: {value:,}")
            else:
                response_lines.append(f"• {formatted_key}: {str(value)}")
        
        response_lines.append(f"")
        response_lines.append("Key Insights:")
        
        # Generate insights WITHOUT asterisks
        if 'total' in str(data).lower() or 'sum' in str(data).lower():
            response_lines.append("1. Total metrics provide overall performance indicators")
            response_lines.append("2. Consider comparing with historical data")
            response_lines.append("3. Break down by time periods for trend analysis")
        
        elif 'average' in str(data).lower() or 'avg' in str(data).lower():
            response_lines.append("1. Average values indicate central tendency")
            response_lines.append("2. Consider calculating median for skewed distributions")
            response_lines.append("3. Review minimum and maximum values for context")
        
        elif 'count' in str(data).lower():
            response_lines.append("1. Count metrics show volume and frequency")
            response_lines.append("2. Consider conversion rates if applicable")
            response_lines.append("3. Track changes over time for trend analysis")
        
        return "\n".join(response_lines)
    
    @staticmethod
    def enhance_response_structure(response: str) -> str:
        """Enhance existing response with better formatting"""
        # Add bullet points where appropriate
        lines = response.split('\n')
        enhanced_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # Convert asterisk lists to bullet points
            if stripped.startswith('* '):
                enhanced_lines.append(f"• {stripped[2:]}")
            # Convert dash lists to bullet points
            elif stripped.startswith('- '):
                enhanced_lines.append(f"• {stripped[2:]}")
            # Add bold to numbers at start of lines
            elif re.match(r'^\d+[\.\)]', stripped):
                enhanced_lines.append(f"**{stripped}**")
            else:
                enhanced_lines.append(line)
        
        return '\n'.join(enhanced_lines)