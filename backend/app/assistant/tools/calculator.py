# backend/app/assistant/tools/calculator.py
from ._base_tool import BaseTool
import ast
import operator as op
import logging

logger = logging.getLogger(__name__)

# Supported operators (for safer eval)
# Limited set for basic arithmetic
_operators = {
    ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
    ast.Div: op.truediv, ast.Pow: op.pow, # Basic arithmetic
    # ast.BitXor: op.xor, # Bitwise XOR - less common for general calc
    ast.USub: op.neg # Unary minus
}

def _eval_expr(expr):
    """
    Safely evaluates a mathematical expression string using AST.
    Source: Adapted from https://stackoverflow.com/a/9558001/1167783
    """
    try:
        return _eval(ast.parse(expr, mode='eval').body)
    except (TypeError, SyntaxError, KeyError, ZeroDivisionError, RecursionError, OverflowError) as e:
        logger.warning(f"Failed to evaluate expression '{expr}': {e}")
        raise ValueError(f"Invalid or unsupported expression: {e}")
    except Exception as e:
        logger.error(f"Unexpected error evaluating expression '{expr}': {e}", exc_info=True)
        raise ValueError("An unexpected error occurred during calculation.")


def _eval(node):
    """Recursive helper for _eval_expr."""
    if isinstance(node, ast.Constant): # Python 3.8+ uses Constant for numbers/strings
        if isinstance(node.value, (int, float)):
            return node.value
        else:
             raise TypeError(f"Unsupported constant type: {type(node.value)}")
    elif isinstance(node, ast.Num): # Support for older Python versions (pre 3.8)
        return node.n
    elif isinstance(node, ast.BinOp): # <left> <operator> <right>
        operator_func = _operators.get(type(node.op))
        if operator_func:
            return operator_func(_eval(node.left), _eval(node.right))
        else:
            raise TypeError(f"Unsupported binary operator: {type(node.op)}")
    elif isinstance(node, ast.UnaryOp): # <operator> <operand> e.g., -1
        operator_func = _operators.get(type(node.op))
        if operator_func:
            return operator_func(_eval(node.operand))
        else:
             raise TypeError(f"Unsupported unary operator: {type(node.op)}")
    else:
        raise TypeError(f"Unsupported expression type: {type(node)}")


class CalculatorTool(BaseTool):
    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return ("Evaluates simple mathematical arithmetic expressions involving numbers and "
                "operators like +, -, *, /, ** (power). Input should be a single string "
                "containing only the mathematical expression (e.g., '2 + 2 * 5 / (3-1)').")

    def run(self, query: str) -> str:
        """Evaluates the mathematical expression."""
        logger.info(f"Calculator tool running with query: '{query}'")
        try:
            # Basic sanitization: remove potential whitespace
            clean_query = query.strip()
            if not clean_query:
                return "Error: No expression provided."

            result = _eval_expr(clean_query)
            # Format result nicely
            if isinstance(result, float) and result.is_integer():
                result_str = str(int(result))
            else:
                result_str = str(result)

            return f"The result of '{clean_query}' is {result_str}"
        except ValueError as e:
            # Catch errors from _eval_expr
            return f"Error: {e}"
        except Exception as e:
             # Catch any other unexpected errors
             logger.error(f"Unexpected error in CalculatorTool.run for query '{query}': {e}", exc_info=True)
             return f"An unexpected error occurred while trying to calculate."
