import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class ChartGenerator:
    """Generates chart configurations based on data analysis for any database type"""
    
    def __init__(self):
        self.chart_types = {
            'bar': 'bar',
            'line': 'line', 
            'pie': 'pie',
            'scatter': 'scatter',
            'area': 'area'
        }
    
    def analyze_data_for_charts(self, data: Any, query: str) -> Optional[Dict[str, Any]]:
        """Analyze data to determine if it's suitable for charting - works with any database"""
        try:
            if not data:
                logger.warning("❌ No data for chart analysis")
                return None
            
            # Normalize data structure
            normalized_data = self._normalize_data(data)
            
            if not normalized_data:
                logger.warning("❌ Could not normalize data for chart")
                return None
            
            query_lower = query.lower()
            
            # Check if data is list of dictionaries (most common for all DBs)
            if isinstance(normalized_data, list) and len(normalized_data) > 0:
                # First, try to extract categorical data (most common for "average price by category")
                category_chart = self._extract_categorical_data(normalized_data, query_lower)
                if category_chart:
                    logger.info(f"✅ Generated category chart for query: {query}")
                    return category_chart
                
                # Try to extract time-based data
                time_chart = self._extract_time_based_data(normalized_data, query_lower)
                if time_chart:
                    logger.info(f"✅ Generated time-based chart for query: {query}")
                    return time_chart
                
                # Try to extract numeric comparison
                numeric_chart = self._extract_numeric_comparison(normalized_data, query_lower)
                if numeric_chart:
                    logger.info(f"✅ Generated numeric comparison chart for query: {query}")
                    return numeric_chart
            
            # Check if data is aggregated result (single dict)
            elif isinstance(normalized_data, dict):
                aggregated_chart = self._extract_aggregated_chart(normalized_data, query_lower)
                if aggregated_chart:
                    logger.info(f"✅ Generated aggregated chart for query: {query}")
                    return aggregated_chart
            
            logger.warning(f"⚠️ No suitable chart type found for data structure")
            return None
            
        except Exception as e:
            logger.error(f"❌ Chart analysis failed: {e}", exc_info=True)
            return None
    
    def _normalize_data(self, data: Any) -> Any:
        """Normalize data from different database formats to a consistent structure"""
        try:
            if not data:
                return None
            
            # If data is a list
            if isinstance(data, list):
                normalized_list = []
                for item in data:
                    if isinstance(item, dict):
                        # Convert MongoDB ObjectId to string if present
                        if '_id' in item and hasattr(item['_id'], '__str__'):
                            item = item.copy()  # Don't modify original
                            item['id'] = str(item['_id'])
                            # Remove _id to avoid confusion
                            del item['_id']
                        normalized_list.append(item)
                    elif isinstance(item, (int, float, str)):
                        # Wrap single values in dict
                        normalized_list.append({'value': item})
                    else:
                        normalized_list.append(item)
                return normalized_list
            
            # If data is a dict
            elif isinstance(data, dict):
                # Convert MongoDB ObjectId to string if present
                if '_id' in data and hasattr(data['_id'], '__str__'):
                    data = data.copy()
                    data['id'] = str(data['_id'])
                    del data['_id']
                return data
            
            # If data is a single value
            elif isinstance(data, (int, float, str)):
                return [{'value': data}]
            
            return data
            
        except Exception as e:
            logger.error(f"❌ Data normalization failed: {e}")
            return data
    
    def _extract_categorical_data(self, data: List[Dict], query: str) -> Optional[Dict[str, Any]]:
        """Extract categorical data for bar/pie charts - perfect for 'average price by category'"""
        try:
            if len(data) == 0:
                return None
            
            # Look for category fields (for "average price by category", look for 'category' field)
            category_fields = []
            numeric_fields = []
            
            first_item = data[0]
            
            for key in first_item.keys():
                key_lower = key.lower()
                
                # Check for category fields based on query
                query_words = query.lower().split()
                if any(word in key_lower for word in ['category', 'type', 'name', 'product', 'group', 'class']):
                    category_fields.append(key)
                # Also check if key appears in query
                elif any(key_lower in word for word in query_words):
                    category_fields.append(key)
                # Check for numeric fields
                elif self._is_numeric_field(data, key):
                    numeric_fields.append(key)
            
            # If no category fields found, use first non-numeric field as category
            if not category_fields:
                for key in first_item.keys():
                    if key not in numeric_fields and not key.startswith('_') and key not in ['id', '_id']:
                        category_fields.append(key)
                        break
            
            # If no numeric fields found, use first numeric-looking field
            if not numeric_fields:
                for key in first_item.keys():
                    if self._could_be_numeric(data, key):
                        numeric_fields.append(key)
                        break
            
            if category_fields and numeric_fields:
                category_field = category_fields[0]
                numeric_field = numeric_fields[0]
                
                # Group by category and calculate average
                category_totals = {}
                category_counts = {}
                
                for item in data:
                    category = str(item.get(category_field, 'Unknown')).strip()
                    value = item.get(numeric_field)
                    
                    if category not in category_totals:
                        category_totals[category] = 0
                        category_counts[category] = 0
                    
                    if value is not None:
                        try:
                            num_value = float(value) if not isinstance(value, (int, float)) else float(value)
                            category_totals[category] += num_value
                            category_counts[category] += 1
                        except (ValueError, TypeError):
                            continue
                
                # Calculate averages
                averages = {}
                for category, total in category_totals.items():
                    count = category_counts.get(category, 1)
                    averages[category] = total / count if count > 0 else 0
                
                # Sort by average value
                sorted_items = sorted(averages.items(), key=lambda x: x[1], reverse=True)
                labels = [item[0] for item in sorted_items[:10]]  # Top 10 categories
                values = [float(item[1]) for item in sorted_items[:10]]
                
                if labels and values and len(labels) > 1:
                    # Determine chart type based on query
                    chart_type = 'bar'
                    if 'distribution' in query or 'percentage' in query or 'share' in query or 'pie' in query:
                        chart_type = 'pie'
                    
                    chart_title = f'Average {numeric_field.replace("_", " ").title()} by {category_field.replace("_", " ").title()}'
                    
                    return {
                        'type': chart_type,
                        'title': chart_title,
                        'labels': labels,
                        'datasets': [{
                            'label': f'Average {numeric_field.replace("_", " ").title()}',
                            'data': values,
                            'backgroundColor': self._generate_colors(len(values))
                        }],
                        'options': {
                            'responsive': True,
                            'plugins': {
                                'title': {
                                    'display': True,
                                    'text': chart_title
                                }
                            }
                        }
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Categorical chart extraction failed: {e}", exc_info=True)
            return None
    
    def _extract_time_based_data(self, data: List[Dict], query: str) -> Optional[Dict[str, Any]]:
        """Extract time-based data for line/bar charts"""
        try:
            if len(data) == 0:
                return None
            
            # Look for date/time fields
            date_fields = []
            numeric_fields = []
            
            first_item = data[0]
            
            for key in first_item.keys():
                key_lower = key.lower()
                # Check for date fields
                if any(time_word in key_lower for time_word in ['date', 'time', 'month', 'year', 'day', 'quarter', 'period']):
                    date_fields.append(key)
                # Check for numeric fields
                elif self._is_numeric_field(data, key):
                    numeric_fields.append(key)
            
            if date_fields and numeric_fields:
                date_field = date_fields[0]
                numeric_field = numeric_fields[0]
                
                # Prepare data
                date_values = []
                numeric_values = []
                
                # Sort by date if possible
                sorted_data = sorted(data, key=lambda x: self._parse_date(x.get(date_field, '')))
                
                for item in sorted_data[:20]:  # Limit to 20 points
                    date_val = item.get(date_field)
                    num_val = item.get(numeric_field)
                    
                    if date_val is not None and num_val is not None:
                        try:
                            date_str = str(date_val)
                            num_float = float(num_val) if not isinstance(num_val, (int, float)) else float(num_val)
                            date_values.append(date_str[:10])  # Take first 10 chars for date
                            numeric_values.append(num_float)
                        except (ValueError, TypeError):
                            continue
                
                if date_values and numeric_values:
                    # Determine chart type
                    chart_type = 'line'
                    if 'bar' in query or 'comparison' in query or 'compare' in query:
                        chart_type = 'bar'
                    
                    return {
                        'type': chart_type,
                        'title': f'{numeric_field.replace("_", " ").title()} over Time',
                        'labels': date_values,
                        'datasets': [{
                            'label': numeric_field.replace("_", " ").title(),
                            'data': numeric_values,
                            'backgroundColor': '#3b82f6' if chart_type == 'bar' else 'rgba(59, 130, 246, 0.5)',
                            'borderColor': '#3b82f6' if chart_type == 'line' else None,
                            'borderWidth': 2 if chart_type == 'line' else None
                        }],
                        'options': {
                            'responsive': True,
                            'plugins': {
                                'title': {
                                    'display': True,
                                    'text': f'{numeric_field.replace("_", " ").title()} Trends'
                                }
                            }
                        }
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Time-based chart extraction failed: {e}")
            return None
    
    def _extract_numeric_comparison(self, data: List[Dict], query: str) -> Optional[Dict[str, Any]]:
        """Extract numeric comparison data"""
        try:
            if len(data) < 2:
                return None
            
            # Find multiple numeric fields for comparison
            numeric_fields = []
            first_item = data[0]
            
            for key in first_item.keys():
                if self._is_numeric_field(data, key) and key not in ['id', '_id']:
                    numeric_fields.append(key)
            
            if len(numeric_fields) >= 2:
                field1 = numeric_fields[0]
                field2 = numeric_fields[1] if len(numeric_fields) > 1 else numeric_fields[0]
                
                labels = []
                data1 = []
                data2 = []
                
                for i, item in enumerate(data[:10]):
                    label = f"Item {i+1}"
                    if 'name' in item:
                        label = str(item.get('name', label))
                    elif 'category' in item:
                        label = str(item.get('category', label))
                    
                    val1 = item.get(field1, 0)
                    val2 = item.get(field2, 0) if field2 != field1 else 0
                    
                    try:
                        data1.append(float(val1) if not isinstance(val1, (int, float)) else float(val1))
                        data2.append(float(val2) if not isinstance(val2, (int, float)) else float(val2))
                        labels.append(label)
                    except (ValueError, TypeError):
                        continue
                
                if labels and data1 and data2:
                    return {
                        'type': 'bar',
                        'title': f'{field1.replace("_", " ").title()} vs {field2.replace("_", " ").title()}',
                        'labels': labels,
                        'datasets': [
                            {
                                'label': field1.replace("_", " ").title(),
                                'data': data1,
                                'backgroundColor': '#3b82f6'
                            },
                            {
                                'label': field2.replace("_", " ").title(),
                                'data': data2,
                                'backgroundColor': '#10b981'
                            }
                        ],
                        'options': {
                            'responsive': True,
                            'plugins': {
                                'title': {
                                    'display': True,
                                    'text': 'Comparison Chart'
                                }
                            }
                        }
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Numeric comparison extraction failed: {e}")
            return None
    
    def _extract_aggregated_chart(self, data: Dict, query: str) -> Optional[Dict[str, Any]]:
        """Extract chart from aggregated data (single result like {'average_price': 123.45})"""
        try:
            if not data:
                return None
            
            # Filter out non-numeric and internal fields
            filtered_data = {}
            for key, value in data.items():
                if key not in ['id', '_id'] and not key.startswith('_'):
                    if isinstance(value, (int, float)):
                        filtered_data[key] = value
                    elif value is not None:
                        try:
                            filtered_data[key] = float(value)
                        except (ValueError, TypeError):
                            continue
            
            if filtered_data:
                labels = []
                values = []
                
                for key, value in filtered_data.items():
                    labels.append(key.replace('_', ' ').title())
                    values.append(float(value))
                
                # Determine chart type based on number of items
                chart_type = 'bar' if len(labels) > 1 else 'pie'
                
                return {
                    'type': chart_type,
                    'title': 'Aggregated Results',
                    'labels': labels,
                    'datasets': [{
                        'label': 'Values',
                        'data': values,
                        'backgroundColor': self._generate_colors(len(values))
                    }],
                    'options': {
                        'responsive': True,
                        'plugins': {
                            'title': {
                                'display': True,
                                'text': 'Summary Chart'
                            }
                        }
                    }
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Aggregated chart extraction failed: {e}")
            return None
    
    def _is_numeric_field(self, data: List[Dict], field: str) -> bool:
        """Check if a field contains numeric data"""
        try:
            if not data:
                return False
            
            # Check first few items
            numeric_count = 0
            total_checked = min(5, len(data))
            
            for i in range(total_checked):
                item = data[i]
                value = item.get(field)
                if value is None:
                    continue
                
                if isinstance(value, (int, float)):
                    numeric_count += 1
                else:
                    # Try to convert to float
                    try:
                        float(str(value))
                        numeric_count += 1
                    except (ValueError, TypeError):
                        pass
            
            # Consider it numeric if at least half the checked items are numeric
            return numeric_count >= total_checked / 2
            
        except Exception:
            return False
    
    def _could_be_numeric(self, data: List[Dict], field: str) -> bool:
        """More lenient check for numeric fields"""
        try:
            if not data:
                return False
            
            for i in range(min(3, len(data))):
                item = data[i]
                value = item.get(field)
                if value is None:
                    continue
                
                # Check common numeric field names
                if any(num_word in field.lower() for num_word in ['price', 'amount', 'total', 'sum', 'avg', 'average', 'count', 'quantity', 'value']):
                    return True
                
                # Try to convert
                try:
                    float(str(value))
                    return True
                except (ValueError, TypeError):
                    continue
            
            return False
        except:
            return False
    
    def _parse_date(self, date_str) -> datetime:
        """Parse date string to datetime"""
        try:
            if isinstance(date_str, datetime):
                return date_str
            
            if not date_str:
                return datetime.min
            
            # Try different date formats
            date_formats = [
                '%Y-%m-%d',
                '%Y-%m-%d %H:%M:%S',
                '%Y/%m/%d',
                '%d-%m-%Y',
                '%d/%m/%Y',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%S.%fZ',
                '%Y%m%d',
                '%m/%d/%Y'
            ]
            
            date_str = str(date_str)
            
            for fmt in date_formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            # Try to extract date from string
            date_patterns = [
                r'(\d{4}-\d{2}-\d{2})',
                r'(\d{2}/\d{2}/\d{4})',
                r'(\d{4}/\d{2}/\d{2})'
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, date_str)
                if match:
                    date_part = match.group(1)
                    for fmt in date_formats:
                        try:
                            return datetime.strptime(date_part, fmt)
                        except ValueError:
                            continue
            
            return datetime.min
            
        except Exception:
            return datetime.min
    
    def _generate_colors(self, count: int) -> List[str]:
        """Generate color palette"""
        colors = [
            '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
            '#06b6d4', '#84cc16', '#f97316', '#6366f1', '#ec4899',
            '#14b8a6', '#f43f5e', '#0ea5e9', '#22c55e', '#eab308'
        ]
        
        if count <= len(colors):
            return colors[:count]
        
        # Generate additional colors if needed
        import colorsys
        additional = []
        for i in range(count - len(colors)):
            hue = i / max(count - len(colors), 1)
            rgb = colorsys.hsv_to_rgb(hue, 0.7, 0.9)
            color = '#{:02x}{:02x}{:02x}'.format(
                int(rgb[0] * 255),
                int(rgb[1] * 255),
                int(rgb[2] * 255)
            )
            additional.append(color)
        
        return colors + additional
    
    def generate_chart_description(self, chart_config: Dict[str, Any]) -> str:
        """Generate description text for the chart"""
        try:
            chart_type = chart_config.get('type', 'chart')
            title = chart_config.get('title', 'Data Visualization')
            
            if chart_type == 'line':
                desc = f"Line chart showing trends over time for {title}."
            elif chart_type == 'bar':
                desc = f"Bar chart comparing values across different categories for {title}."
            elif chart_type == 'pie':
                desc = f"Pie chart showing distribution percentages for {title}."
            else:
                desc = f"Chart visualization for {title}."
            
            return desc
        except:
            return "Data visualization is available."