from typing import Dict, List, Optional, Tuple
import re
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.models import (
    ProposalBlock, BlockLibrary, ProposalType,
    ProposalTemplate, BlockVariable
)


class BlockComposer:
    """Service for composing proposals from modular blocks."""

    def __init__(self, db: Session):
        self.db = db

    def compose_proposal(
        self,
        proposal_type_id: Optional[int],
        template_id: Optional[int],
        extracted_data: Dict,
        custom_block_order: List[str] = None
    ) -> Tuple[List[Dict], List[str]]:
        """
        Compose ordered list of blocks for a proposal.

        Args:
            proposal_type_id: ID of proposal type (e.g., firewall, SOC)
            template_id: ID of template for block ordering
            extracted_data: Dict of extracted field values for variable substitution
            custom_block_order: Optional custom block ordering

        Returns:
            Tuple of (rendered_blocks, missing_variables)
        """
        # Load blocks
        blocks = self._load_blocks(proposal_type_id, template_id)

        # Apply conditional logic
        filtered_blocks = self._apply_conditions(blocks, extracted_data)

        # Apply custom order if provided
        if custom_block_order:
            filtered_blocks = self._apply_custom_order(filtered_blocks, custom_block_order)
        else:
            # Sort by section_order, then subsection_order
            filtered_blocks.sort(key=lambda b: (b['section_order'], b['subsection_order']))

        # Apply default variables
        extracted_data = self._apply_default_variables(filtered_blocks, extracted_data)

        # Track missing variables
        all_required_vars = set()
        for block in filtered_blocks:
            all_required_vars.update(block.get('required_variables', []))
        missing_variables = [v for v in all_required_vars if not extracted_data.get(v)]

        # Render variables in each block
        rendered_blocks = []
        for block in filtered_blocks:
            rendered = self._render_block(block, extracted_data)
            rendered_blocks.append(rendered)

        return rendered_blocks, missing_variables

    def _load_blocks(
        self,
        proposal_type_id: Optional[int],
        template_id: Optional[int]
    ) -> List[Dict]:
        """Load blocks based on proposal type and template."""
        # First, try to use template's block_order if available
        template_block_order = None
        if template_id:
            template = self.db.query(ProposalTemplate).filter(
                ProposalTemplate.id == template_id
            ).first()
            if template and template.block_order:
                template_block_order = template.block_order

        # Query blocks:
        # 1. Static blocks (proposal_type_id IS NULL - applies to all)
        # 2. Type-specific blocks (proposal_type_id matches OR is NULL)
        query = self.db.query(ProposalBlock).join(
            BlockLibrary, ProposalBlock.library_id == BlockLibrary.id
        ).outerjoin(
            ProposalType, ProposalBlock.proposal_type_id == ProposalType.id
        ).filter(
            ProposalBlock.is_active == True
        )

        # For blocks with proposal_type_id, only include matching or NULL
        type_filter = or_(
            ProposalBlock.proposal_type_id == proposal_type_id,
            ProposalBlock.proposal_type_id == None
        )

        # For static library blocks (is_system), always include
        static_filter = BlockLibrary.is_system == True
        blocks_query = query.filter(or_(type_filter, static_filter))

        blocks = blocks_query.all()

        # Convert to dicts
        block_dicts = []
        for b in blocks:
            block_dict = {
                'id': b.id,
                'library_id': b.library_id,
                'library_name': b.library.name if b.library else '',
                'library_is_system': b.library.is_system if b.library else False,
                'proposal_type_id': b.proposal_type_id,
                'proposal_type_name': b.proposal_type.name if b.proposal_type else None,
                'name': b.name,
                'block_key': b.block_key,
                'content': b.content,
                'block_type': b.block_type,
                'required_variables': b.required_variables or [],
                'default_variables': b.default_variables or {},
                'section_order': b.section_order,
                'subsection_order': b.subsection_order,
                'condition_expression': b.condition_expression,
                'is_active': b.is_active
            }
            block_dicts.append(block_dict)

        return block_dicts

    def _apply_conditions(self, blocks: List[Dict], extracted_data: Dict) -> List[Dict]:
        """Filter blocks based on conditional expressions."""
        filtered = []
        for block in blocks:
            if not block.get('condition_expression'):
                filtered.append(block)
                continue
            try:
                if self._evaluate_condition(block['condition_expression'], extracted_data):
                    filtered.append(block)
            except Exception:
                # If condition evaluation fails, include the block (fail open)
                filtered.append(block)
        return filtered

    def _evaluate_condition(self, expr: str, data: Dict) -> bool:
        """
        Safely evaluate condition expressions.

        Supports patterns like:
        - "protocols and 'modbus' in protocols"
        - "proposal_type == 'firewall_deployment'"
        - "site_count > 1"
        """
        # Simple expression parser - handles common patterns
        expr = expr.strip()

        # Handle "X and Y" patterns
        if ' and ' in expr:
            parts = expr.split(' and ')
            return all(self._evaluate_condition(p, data) for p in parts)

        # Handle "X or Y" patterns
        if ' or ' in expr:
            parts = expr.split(' or ')
            return any(self._evaluate_condition(p, data) for p in parts)

        # Handle membership tests: "'modbus' in protocols"
        in_match = re.match(r"'(.+?)'\s+in\s+(\w+)", expr)
        if in_match:
            item, list_var = in_match.groups()
            list_value = data.get(list_var, '')
            if isinstance(list_value, str):
                return item.lower() in list_value.lower()
            return item in list_value

        # Handle equality: "proposal_type == 'value'"
        eq_match = re.match(r"(\w+)\s*==\s*'(.+?)'", expr)
        if eq_match:
            var, value = eq_match.groups()
            return str(data.get(var, '')).lower() == value.lower()

        # Handle comparison: "site_count > 1"
        cmp_match = re.match(r"(\w+)\s*([><=]+)\s*(\d+)", expr)
        if cmp_match:
            var, op, val = cmp_match.groups()
            var_val = data.get(var, 0)
            try:
                var_val = float(var_val)
                val = float(val)
                if op == '>':
                    return var_val > val
                elif op == '<':
                    return var_val < val
                elif op == '>=':
                    return var_val >= val
                elif op == '<=':
                    return var_val <= val
                elif op == '==':
                    return var_val == val
            except (ValueError, TypeError):
                return False

        # Handle simple variable presence check
        if expr in data:
            return bool(data[expr])

        return True

    def _apply_custom_order(self, blocks: List[Dict], custom_order: List[str]) -> List[Dict]:
        """Apply custom block ordering."""
        order_map = {key: i for i, key in enumerate(custom_order)}

        def sort_key(block):
            if block['block_key'] in order_map:
                return order_map[block['block_key']]
            # Put unordered blocks at the end
            return 999

        return sorted(blocks, key=sort_key)

    def _apply_default_variables(self, blocks: List[Dict], extracted_data: Dict) -> Dict:
        """Apply default variables from blocks to extracted data."""
        result = extracted_data.copy()

        for block in blocks:
            defaults = block.get('default_variables', {})
            for key, value in defaults.items():
                if key not in result or not result[key]:
                    result[key] = value

        return result

    def _render_block(self, block: Dict, data: Dict) -> Dict:
        """Replace {{variable}} placeholders with values."""
        content = block['content']

        # Handle conditional blocks: {{#if variable}}...{{/if}}
        content = self._render_conditionals(content, data)

        # Handle each loops: {{#each items}}...{{/each}}
        content = self._render_each_loops(content, data)

        # Handle basic variable substitution
        content = self._render_variables(content, data)

        return {**block, 'rendered_content': content}

    def _render_variables(self, content: str, data: Dict) -> str:
        """Replace {{variable}} with values."""
        result = content

        # Find all {{variable}} patterns
        pattern = r'\{\{(\w+)\}\}'
        matches = re.findall(pattern, content)

        for var_name in matches:
            value = data.get(var_name, '')
            if value is None:
                value = ''
            placeholder = f'{{{{{var_name}}}}}'
            result = result.replace(placeholder, str(value))

        # Handle defaults: {{variable|default_value}}
        default_pattern = r'\{\{(\w+)\|([^{}]+)\}\}'
        default_matches = re.findall(default_pattern, result)

        for var_name, default_value in default_matches:
            placeholder = f'{{{{{var_name}|{default_value}}}}}'
            current_value = data.get(var_name, '')
            if not current_value:
                result = result.replace(placeholder, default_value)
            else:
                result = result.replace(placeholder, str(current_value))

        return result

    def _render_conditionals(self, content: str, data: Dict) -> str:
        """Handle {{#if variable}}...{{/if}} blocks."""
        # Simple implementation - handles basic if/endif
        if_pattern = r'\{\{#if\s+(\w+)\}\}(.*?)\{\{/if\}\}'
        matches = re.findall(if_pattern, content, re.DOTALL)

        result = content
        for var_name, inner_content in matches:
            condition_met = bool(data.get(var_name))
            if condition_met:
                result = result.replace(f'{{{{#if {var_name}}}}}{inner_content}{{{{^if}}}}', inner_content)
            else:
                result = result.replace(f'{{{{#if {var_name}}}}}{inner_content}{{{{^if}}}}', '')

        # Remove any remaining if blocks that weren't matched
        result = re.sub(r'\{\{#if[^}]+\}\}', '', result)
        result = re.sub(r'\{\{/if\}\}', '', result)

        return result

    def _render_each_loops(self, content: str, data: Dict) -> str:
        """Handle {{#each items}}...{{/each}} loops."""
        # Simple implementation for list variables
        each_pattern = r'\{\{#each\s+(\w+)\}\}(.*?)\{\{/each\}\}'
        matches = re.findall(each_pattern, content, re.DOTALL)

        result = content
        for list_name, item_template in matches:
            list_value = data.get(list_name, [])
            if isinstance(list_value, str):
                # Split by newlines if string
                list_value = [v.strip() for v in list_value.split('\n') if v.strip()]

            if not list_value:
                result = result.replace(f'{{{{#each {list_name}}}}}{item_template}{{{{^each}}}}', '')
                continue

            rendered_items = []
            for item in list_value:
                item_content = item_template
                # Replace {{name}} or {{.}} with item value
                if isinstance(item, dict):
                    for k, v in item.items():
                        item_content = item_content.replace(f'{{{{{k}}}}}', str(v))
                else:
                    item_content = item_content.replace('{{.}}', str(item))
                rendered_items.append(item_content)

            rendered_loop = '\n'.join(rendered_items)
            result = result.replace(f'{{{{#each {list_name}}}}}{item_template}{{{{^each}}}}', rendered_loop)

        return result

    def get_available_blocks(self, proposal_type_id: Optional[int] = None) -> List[Dict]:
        """Get all available blocks, optionally filtered by proposal type."""
        query = self.db.query(ProposalBlock).join(
            BlockLibrary, ProposalBlock.library_id == BlockLibrary.id
        ).outerjoin(
            ProposalType, ProposalBlock.proposal_type_id == ProposalType.id
        ).filter(
            ProposalBlock.is_active == True
        )

        if proposal_type_id:
            type_filter = or_(
                ProposalBlock.proposal_type_id == proposal_type_id,
                ProposalBlock.proposal_type_id == None,
                BlockLibrary.is_system == True
            )
            query = query.filter(type_filter)

        blocks = query.all()

        return [
            {
                'id': b.id,
                'library_id': b.library_id,
                'library_name': b.library.name if b.library else '',
                'name': b.name,
                'block_key': b.block_key,
                'block_type': b.block_type,
                'section_order': b.section_order,
                'required_variables': b.required_variables or []
            }
            for b in blocks
        ]


def substitute_variables(content: str, variables: Dict) -> str:
    """
    Standalone function for simple variable substitution.

    Args:
        content: Template content with {{variable}} placeholders
        variables: Dict mapping variable names to values

    Returns:
        Content with variables replaced
    """
    composer = BlockComposer.__new__(BlockComposer)
    return composer._render_variables(content, variables)