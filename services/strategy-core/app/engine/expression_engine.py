import ast
import operator
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

class SecurityException(Exception):
    pass

class ExpressionEngine:
    def __init__(self):
        self.allowed_operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
            ast.Mod: operator.mod,
            # Comparisons
            ast.Gt: operator.gt,
            ast.Lt: operator.lt,
            ast.GtE: operator.ge,
            ast.LtE: operator.le,
            ast.Eq: operator.eq,
            ast.NotEq: operator.ne,
        }
        
        # DataFrame/Series operations
        self.functions = {
            # Time Series
            'delay': lambda x, n: x.shift(n),
            'delta': lambda x, n: x.diff(n),
            'ts_max': lambda x, n: x.rolling(n).max(),
            'ts_min': lambda x, n: x.rolling(n).min(),
            'sma': lambda x, n: x.rolling(n).mean(),
            'std': lambda x, n: x.rolling(n).std(),
            'ts_rank': lambda x, n: x.rolling(n).rank(pct=True), # Added for hybrid strategy
            
            # Cross Sectional
            'rank': lambda x: x.rank(axis=1, pct=True) if isinstance(x, pd.DataFrame) else x.rank(pct=True),
            
            # Math
            'log': np.log,
            'sqrt': np.sqrt,
            'abs': np.abs,
            'sign': np.sign,
        }

    def validate(self, formula: str):
        """
        Parses formula and returns True if safe/valid, else raises SecurityException.
        """
        if "__" in formula or "import" in formula:
             raise SecurityException("Unsafe characters detected")

        try:
            tree = ast.parse(formula, mode='eval')
        except SyntaxError as e:
            raise SecurityException(f"Syntax Error: {e}")

        # Complexity Check
        if len(list(ast.walk(tree))) > 50:
             raise SecurityException("Formula too complex (max nodes exceeded)")

        for node in ast.walk(tree):
            if isinstance(node, (ast.Expression, ast.Load, ast.Constant, 
                                 ast.Name, ast.BinOp, ast.UnaryOp, ast.Call, ast.keyword, ast.Compare, ast.cmpop,
                                 ast.operator, ast.unaryop)):
                continue
            if isinstance(node, ast.Attribute):
                # Strictly disallow attributes for now
                raise SecurityException(f"Attribute access not allowed: {node}")
            
            raise SecurityException(f"Node type not allowed: {type(node).__name__}")
        
        return True

    def evaluate(self, formula: str, context: dict[str, pd.DataFrame]):
        """
        Safe evaluation of formula using AST walking.
        args:
            formula: string like "rank(close / delay(close, 5))"
            context: dict mapping variable names to DataFrames (e.g. {'close': df})
        """
        self.validate(formula)
        tree = ast.parse(formula, mode='eval')
        return self._eval_node(tree.body, context)

    def _eval_node(self, node, context):
        if isinstance(node, ast.BinOp):
            left = self._eval_node(node.left, context)
            right = self._eval_node(node.right, context)
            op = type(node.op)
            if op not in self.allowed_operators:
                raise SecurityException(f"Operator {op} not supported")
            return self.allowed_operators[op](left, right)

        elif isinstance(node, ast.Compare):
            left = self._eval_node(node.left, context)
            # Handle chained comparisons if needed, but for now simple x > y
            if len(node.ops) != 1:
                 raise SecurityException("Chained comparisons not supported")
            
            op = type(node.ops[0])
            right = self._eval_node(node.comparators[0], context)
            
            if op not in self.allowed_operators:
                raise SecurityException(f"Operator {op} not supported")
            return self.allowed_operators[op](left, right)
        
        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand, context)
            op = type(node.op)
            if op not in self.allowed_operators:
                raise SecurityException(f"Operator {op} not supported")
            return self.allowed_operators[op](operand)
            
        elif isinstance(node, ast.Name):
            if node.id in context:
                return context[node.id]
            raise SecurityException(f"Variable '{node.id}' not found in context")
            
        elif isinstance(node, ast.Constant):
            return node.value
            
        elif isinstance(node, ast.Call):
            func_name = node.func.id
            if func_name not in self.functions:
                raise SecurityException(f"Function '{func_name}' not supported")
            
            args = [self._eval_node(arg, context) for arg in node.args]
            return self.functions[func_name](*args)
            
        else:
            raise SecurityException(f"Unexpected node: {type(node).__name__}")
