from django import template
from django.utils.translation import gettext_lazy as _
import re

register = template.Library()

class ExprNode(template.Node):
    def __init__(self, expr_string, var_name):
        self.expr_string = expr_string
        self.var_name = var_name
   
    def flattenContext(self, context):
      if type(context) == dict :
        return context
      else :
        d = {}
        for item in context :
          d.update(self.flattenContext(item))
        return d

    def render(self, context):
      d = {}
      d['_'] = _
      d.update(self.flattenContext(context))
      
      # Check if to display result or store it in template vars.
      if self.var_name:
          context[self.var_name] = eval(self.expr_string, d)
          return ''
      else:
          return str(eval(self.expr_string, d))

r_expr = re.compile(r'(.*?)\s+as\s+(\w+)', re.DOTALL)    
def do_expr(parser, token):
    try:
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires arguments" % token.contents[0]
    m = r_expr.search(arg)
    if m:
        expr_string, var_name = m.groups()
    else:
        if not arg:
            raise template.TemplateSyntaxError, "%r tag at least require one argument" % tag_name
            
        expr_string, var_name = arg, None
    return ExprNode(expr_string, var_name)
do_expr = register.tag('expr', do_expr)
