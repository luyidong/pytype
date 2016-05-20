"""Tests for handling PYI code."""


from pytype import utils
from pytype.tests import test_inference


class PYITest(test_inference.InferenceTest):
  """Tests for PYI."""

  def testOptional(self):
    with utils.Tempdir() as d:
      d.create_file("mod.pyi", """
        def f(x: int = ...) -> None
      """)
      with self.Infer("""\
        import mod
        def f():
          return mod.f()
        def g():
          return mod.f(3)
      """, deep=True, solve_unknowns=False,
                      extract_locals=True,  # TODO(kramm): Shouldn't need this.
                      pythonpath=[d.path]) as ty:
        self.assertTypesMatchPytd(ty, """
          mod = ...  # type: module
          def f() -> NoneType
          def g() -> NoneType
        """)

  def testSolve(self):
    with utils.Tempdir() as d:
      d.create_file("mod.pyi", """
        def f(node: int, *args, **kwargs) -> str
      """)
      with self.Infer("""\
        import mod
        def g(x):
          return mod.f(x)
      """, deep=True, solve_unknowns=True, pythonpath=[d.path]) as ty:
        self.assertTypesMatchPytd(ty, """
          mod = ...  # type: module
          def g(x: int) -> str
        """)

  def testTyping(self):
    with utils.Tempdir() as d:
      d.create_file("mod.pyi", """
        from typing import Optional, List, Any, IO
        def split(s: Optional[float]) -> List[str, ...]: ...
      """)
      with self.Infer("""\
        import mod
        def g(x):
          return mod.split(x)
      """, deep=True, solve_unknowns=True, pythonpath=[d.path]) as ty:
        self.assertTypesMatchPytd(ty, """
          mod = ...  # type: module
          def g(x: NoneType or float) -> List[str, ...]
        """)

  def testClasses(self):
    with utils.Tempdir() as d:
      d.create_file("classes.pyi", """
        class A(object):
          def foo(self) -> A
        class B(A):
          pass
      """)
      with self.Infer("""\
        import classes
        x = classes.B().foo()
      """, deep=False, solve_unknowns=False, pythonpath=[d.path]) as ty:
        self.assertTypesMatchPytd(ty, """
          classes = ...  # type: module
          x = ...  # type: classes.A
        """)

  def testEmptyModule(self):
    with utils.Tempdir() as d:
      d.create_file("vague.pyi", """
        def __getattr__(name) -> Any
      """)
      with self.Infer("""\
        import vague
        x = vague.foo + vague.bar
      """, deep=False, solve_unknowns=False, pythonpath=[d.path]) as ty:
        self.assertTypesMatchPytd(ty, """
          vague = ...  # type: module
          x = ...  # type: Any
        """)

  def testDecorators(self):
    with utils.Tempdir() as d:
      d.create_file("decorated.pyi", """
        class A(object):
          @staticmethod
          def u(a, b) -> int: ...
          @classmethod
          def v(cls, a, b) -> int: ...
          def w(self, a, b) -> int: ...
      """)
      with self.Infer("""\
        import decorated
        u = decorated.A.u(1, 2)
        v = decorated.A.v(1, 2)
        a = decorated.A()
        x = a.u(1, 2)
        y = a.v(1, 2)
        z = a.w(1, 2)
      """, deep=False, solve_unknowns=False, extract_locals=True,
                      pythonpath=[d.path]) as ty:
        self.assertTypesMatchPytd(ty, """
          decorated = ...  # type: module
          a = ...  # type: decorated.A
          u = ...  # type: int
          v = ...  # type: int
          x = ...  # type: int
          y = ...  # type: int
          z = ...  # type: int
        """)

  def testPassPyiClassmethod(self):
    with utils.Tempdir() as d:
      d.create_file("a.pyi", """
        class A(object):
          @classmethod
          def v(cls) -> float: ...
          def w(self, x: classmethod) -> int: ...
      """)
      with self.Infer("""\
        import a
        u = a.A().w(a.A.v)
      """, deep=False, solve_unknowns=False, extract_locals=True,
                      pythonpath=[d.path]) as ty:
        self.assertTypesMatchPytd(ty, """
          a = ...  # type: module
          u = ...  # type: int
        """)

  def testOptionalParameters(self):
    with utils.Tempdir() as d:
      d.create_file("a.pyi", """
        def parse(source, filename = ..., mode = ..., *args, **kwargs) -> int: ...
      """)
      with self.Infer("""\
        import a
        u = a.parse("True")
      """, deep=False, solve_unknowns=True, pythonpath=[d.path]) as ty:
        self.assertTypesMatchPytd(ty, """
          a = ...  # type: module
          u = ...  # type: int
        """)

  def testOptimize(self):
    with utils.Tempdir() as d:
      d.create_file("a.pyi", """
        class Bar(dict[?, int]): ...
      """)
      with self.Infer("""\
      import a
      def f(foo, bar):
        return __any_object__[1]
      def g():
        out = f('foo', 'bar')
        out = out.split()
      """, deep=True, solve_unknowns=True, pythonpath=[d.path]) as ty:
        self.assertTypesMatchPytd(ty, """
          a = ...  # type: module
          def f(foo, bar) -> Union[a.Bar, bytearray, str, unicode]: ...
          def g() -> NoneType: ...
        """)

  def testIterable(self):
    with utils.Tempdir() as d:
      d.create_file("a.pyi", """
        def f(l: Iterable[int]) -> int: ...
      """)
      with self.Infer("""\
        import a
        u = a.f([1, 2, 3])
      """, deep=False, pythonpath=[d.path], extract_locals=True) as ty:
        self.assertTypesMatchPytd(ty, """
          a = ...  # type: module
          u = ...  # type: int
        """)


if __name__ == "__main__":
  test_inference.main()
