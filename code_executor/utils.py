import ast
import astor


class CodeTransformer:
    def __init__(self, code):
        self.code = code
        self.tree = ast.parse(code)

    def add_try_except(self, error_handler: "ErrorHandler"):
        try_body = self.tree.body
        except_body = error_handler.get_except_body(var_names=self.get_variable_names())

        try_except = ast.Try(
            body=try_body,
            handlers=[ast.ExceptHandler(type=ast.Name(id="Exception", ctx=ast.Load()), name="e", body=except_body)],
            orelse=[],
            finalbody=[],
        )

        self.tree.body = [try_except]
        return self

    def to_source(self):
        return astor.to_source(self.tree)

    def get_variable_names(self) -> set:
        """解析代码并获取变量名。"""
        tree = self.tree
        variable_names = set()

        class VariableVisitor(ast.NodeVisitor):
            def visit_Name(self, node):
                if isinstance(node.ctx, ast.Store):
                    variable_names.add(node.id)

        visitor = VariableVisitor()
        visitor.visit(tree)
        return variable_names


class ErrorHandler(object):
    def get_except_body(self, **kwargs):
        raise NotImplementedError("Subclasses must implement this method")


class PrintErrorHandler(ErrorHandler):
    def get_except_body(self, **kwargs):
        return [
            ast.Expr(
                value=ast.Call(
                    func=ast.Name(id="print", ctx=ast.Load()),
                    args=[ast.Constant(value="An error occurred: "), ast.Name(id="e", ctx=ast.Load())],
                    keywords=[],
                )
            ),
            ast.Expr(
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id="traceback", ctx=ast.Load()), attr="print_exc", ctx=ast.Load()
                    ),
                    args=[],
                    keywords=[],
                )
            ),
        ]


class PrintErrorWithVariablesHandler(PrintErrorHandler):
    def get_except_body(self, var_names: set):
        except_body = super().get_except_body()
        for var in var_names:
            except_body.append(
                ast.If(
                    test=ast.Compare(
                        left=ast.Constant(value=var),
                        ops=[ast.In()],
                        comparators=[ast.Call(func=ast.Name(id="locals", ctx=ast.Load()), args=[], keywords=[])],
                    ),
                    body=[
                        ast.Expr(
                            value=ast.Call(
                                func=ast.Name(id="print", ctx=ast.Load()),
                                args=[
                                    ast.Constant(value=f"Value of {var}: "),
                                    ast.Subscript(
                                        value=ast.Call(
                                            func=ast.Name(id="locals", ctx=ast.Load()), args=[], keywords=[]
                                        ),
                                        slice=ast.Index(value=ast.Constant(value=var)),
                                        ctx=ast.Load(),
                                    ),
                                ],
                                keywords=[],
                            )
                        )
                    ],
                    orelse=[],  # 如果键不存在，则不执行任何操作
                )
            )
        return except_body


if __name__ == "__main__":
    # 使用示例
    code = "import traceback;x = 1;y=0;z=x/y"
    transformer = CodeTransformer(code)

    # 使用 PrintErrorWithVariablesHandler 添加 try-except 语句
    transformer.add_try_except(PrintErrorWithVariablesHandler()).to_source()

    new_code = transformer.to_source()
    print(new_code)
    exec(new_code)
