Layout form wrapper
===================

Layout wrapper views are used for two purposes:

* To avoid having to mix Zope2-isms into form classes in Zope 2.11 and
  earlier. (In Zope 2.12, the changes to the acquisition mechanism means that
  standard z3c.form forms can be used directly without having to mix in
  acquisition anyway)
* To avoid separate form templates from layout templates (aka the main
  template), to allow a single form to be usable in different contexts,
  e.g. as a standalone form or a viewlet.

If you are using Zope 2.12 or later, you don't need to use the wrapper view
if you don't want to, so long as you have loaded the plone.z3cform
configuration.

To use the wrapper, you can call the ``wrap_form`` function defined in the
``layout`` module to create a view that's suitable for registration with a
``browser:page`` directive::

    >>> from zope.interface import alsoProvides
    >>> from zope.publisher.browser import TestRequest
    >>> from zope.annotation.interfaces import IAttributeAnnotatable
    >>> from z3c.form.interfaces import IFormLayer

    >>> def make_request(form={}):
    ...     request = TestRequest()
    ...     request.form.update(form)
    ...     alsoProvides(request, IFormLayer)
    ...     alsoProvides(request, IAttributeAnnotatable)
    ...     return request

Then we create a simple form::

    >>> from zope import interface, schema
    >>> from z3c.form import form, field, button
    >>> from plone.z3cform.layout import FormWrapper

    >>> class MySchema(interface.Interface):
    ...     age = schema.Int(title=u'Age')

    >>> from z3c.form.interfaces import IFieldsForm
    >>> from zope.interface import implementer
    >>> @implementer(IFieldsForm)
    ... class MyForm(form.Form):
    ...     fields = field.Fields(MySchema)
    ...     ignoreContext = True  # don't use context to get widget data
    ...
    ...     @button.buttonAndHandler(u'Apply')
    ...     def handleApply(self, action):
    ...         data, errors = self.extractData()
    ...         print(data['age'])  # ... or do stuff

    >>> class MyFormWrapper(FormWrapper):
    ...     form = MyForm
    ...     label = u'Please enter your age'

    >>> from zope.component import provideAdapter
    >>> from zope.publisher.interfaces.browser import IBrowserRequest
    >>> from zope.interface import Interface

    >>> provideAdapter(adapts=(Interface, IBrowserRequest),
    ...                provides=Interface,
    ...                factory=MyFormWrapper,
    ...                name=u'test-form')

For our context, we define a class that inherits from Acquisition.
This is to satisfy permission checking later on, and it'll allow the
layout view to call ``aq_inner`` on the context::

    >>> from Acquisition import Implicit
    >>> @implementer(Interface)
    ... class Bar(Implicit):
    ...     __allow_access_to_unprotected_subobjects__ = 1

Let's verify that worked::

    >>> from zope.component import getMultiAdapter
    >>> context = Bar()
    >>> request = make_request()
    >>> getMultiAdapter((context, request), name=u'test-form')
    ... # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
    <MyFormWrapper object ...>

We can also use a function called ``wrap_form`` to wrap our form in a
layout.  We define a custom layout template first::

    >>> import os
    >>> import tempfile
    >>> from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
    >>> fd, path = tempfile.mkstemp()
    >>> with os.fdopen(fd, 'w') as fio:
    ...     _ = fio.write("""
    ... <html>Hello, this is your layout speaking:
    ... <h1 tal:content="view/label">View Title</h1>
    ... <div tal:content="structure view/contents"></div>
    ... </html>""")
    >>> layout = ViewPageTemplateFile(path, _prefix='')

Note that the ``_prefix`` argument passed to Five's
ViewPageTemplateFile is unnecessary when outside of a test.  We can
now make the actual call to ``wrap_form`` and register the view class
it returns.  Normally, you'd register this view class using ZCML, like
with any other view.

::

    >>> from plone.z3cform.layout import wrap_form
    >>> view_class = wrap_form(MyForm, index=layout, label=u'My label')
    >>> provideAdapter(adapts=(Interface, IBrowserRequest),
    ...                provides=Interface,
    ...                factory=view_class,
    ...                name=u'test-form2')

Let's render this view::

    >>> view = getMultiAdapter(
    ...     (context, request), name=u'test-form2')
    >>> print(view())  # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
    <html>Hello, this is your layout speaking:...My label...Age...</html>

If we don't pass the label to ``wrap_form``, it'll try to look up the
label from the form instance::

    >>> class MyLabelledForm(MyForm):
    ...     @property
    ...     def label(self):
    ...         return 'Another label'

    >>> view_class = wrap_form(MyLabelledForm, index=layout)
    >>> view = view_class(context, request)
    >>> print(view())  # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
    <html>Hello, this is your layout speaking:...Another label...Age...</html>


Send bad data to the form::

    >>> request = make_request(form={'form.widgets.age': '12.1'})
    >>> from zope.interface import Interface
    >>> formWrapper = getMultiAdapter((context, request), name=u"test-form")
    >>> form = formWrapper.form(context, request)
    >>> form.update()
    >>> data, errors = form.extractData()
    >>> data
    {}
    >>> errors
    (<ValueErrorViewSnippet for ValueError>,)

And then send correct data to the form::

    >>> request = make_request(form={'form.widgets.age': '12'})
    >>> from zope.interface import Interface
    >>> from Acquisition import Implicit
    >>> formWrapper = getMultiAdapter((context, request), name=u'test-form')
    >>> form = formWrapper.form(context, request)
    >>> form.update()
    >>> data, errors = form.extractData()
    >>> data
    {'age': 12}
    >>> errors
    ()

We also have the option of defining a default layout template for all forms
that don't specify a particular 'index' template. Here, we use the 'path'
function from plone.z3cform.templates to locate a template file (the default
template, in fact) from the plone.z3cform directory. For your own purposes,
you probably just want to specify a filename relative to your package.

::

    >>> new_view_class = wrap_form(MyLabelledForm)
    >>> view = new_view_class(context, request)

    >>> from plone.z3cform.templates import ZopeTwoFormTemplateFactory
    >>> layout_factory = ZopeTwoFormTemplateFactory(
    ...     path, form=new_view_class)

Note that the 'form' parameter here should be the wrapper view class, or an
interface implemented by it, not the form class itself.

::

    >>> provideAdapter(layout_factory)
    >>> print(view())  # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
    <html>Hello, this is your layout speaking:...Another label...Age...</html>

Clean up:

    >>> os.unlink(path)
