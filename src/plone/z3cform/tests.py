# -*- coding: utf-8 -*-
from plone.testing import Layer
from plone.testing import layered
from plone.testing import zope
from plone.testing import zca
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from z3c.form.interfaces import IFormLayer
from zope import component
from zope import interface
from zope.component import testing
from zope.configuration import xmlconfig
from zope.publisher.browser import TestRequest as BaseTestRequest

import doctest
import plone.z3cform.templates
import re
import six
import unittest


@interface.implementer(IFormLayer)
class TestRequest(BaseTestRequest):
    pass


def create_eventlog(event=interface.Interface):
    value = []

    @component.adapter(event)
    def log(event):
        value.append(event)

    component.provideHandler(log)
    return value


def setup_defaults():
    # Set up z3c.form defaults
    from z3c.form import browser, button, converter, datamanager, error, field
    from z3c.form import interfaces, validator, widget
    from z3c.form.browser import text
    from zope.pagetemplate.interfaces import IPageTemplate
    import os.path
    import zope.schema

    def getPath(filename):
        return os.path.join(os.path.dirname(browser.__file__), filename)

    component.provideAdapter(validator.SimpleFieldValidator)
    component.provideAdapter(validator.InvariantsValidator)
    component.provideAdapter(datamanager.AttributeField)
    component.provideAdapter(field.FieldWidgets)

    component.provideAdapter(
        text.TextFieldWidget,
        adapts=(zope.schema.interfaces.ITextLine, interfaces.IFormLayer),
    )
    component.provideAdapter(
        text.TextFieldWidget,
        adapts=(zope.schema.interfaces.IInt, interfaces.IFormLayer),
    )

    component.provideAdapter(
        widget.WidgetTemplateFactory(getPath('text_input.pt'), 'text/html'),
        (None, None, None, None, interfaces.ITextWidget),
        IPageTemplate,
        name=interfaces.INPUT_MODE,
    )
    component.provideAdapter(
        widget.WidgetTemplateFactory(getPath('text_display.pt'), 'text/html'),
        (None, None, None, None, interfaces.ITextWidget),
        IPageTemplate,
        name=interfaces.DISPLAY_MODE,
    )

    component.provideAdapter(
        widget.WidgetTemplateFactory(
            getPath('checkbox_input.pt'), 'text/html'
        ),
        (None, None, None, None, interfaces.ICheckBoxWidget),
        IPageTemplate,
        name=interfaces.INPUT_MODE,
    )
    component.provideAdapter(
        widget.WidgetTemplateFactory(
            getPath('checkbox_display.pt'), 'text/html'
        ),
        (None, None, None, None, interfaces.ICheckBoxWidget),
        IPageTemplate,
        name=interfaces.DISPLAY_MODE,
    )
    # Submit Field Widget
    component.provideAdapter(
        widget.WidgetTemplateFactory(getPath('submit_input.pt'), 'text/html'),
        (None, None, None, None, interfaces.ISubmitWidget),
        IPageTemplate,
        name=interfaces.INPUT_MODE,
    )

    component.provideAdapter(converter.FieldDataConverter)
    component.provideAdapter(converter.FieldWidgetDataConverter)
    component.provideAdapter(
        button.ButtonAction, provides=interfaces.IButtonAction
    )
    component.provideAdapter(button.ButtonActions)
    component.provideAdapter(button.ButtonActionHandler)
    component.provideAdapter(error.StandardErrorViewTemplate)

    # Make traversal work; register both the default traversable
    # adapter and the ++view++ namespace adapter
    component.provideAdapter(
        zope.traversing.adapters.DefaultTraversable, [None]
    )
    component.provideAdapter(
        zope.traversing.namespace.view, (None, None), name='view'
    )

    # Setup ploneform macros, simlulating the ZCML directive
    plone.z3cform.templates.Macros.index = ViewPageTemplateFile(
        plone.z3cform.templates.path('macros.pt')
    )

    component.provideAdapter(
        plone.z3cform.templates.Macros,
        (None, None),
        zope.publisher.interfaces.browser.IBrowserView,
        name='ploneform-macros',
    )

    # setup plone.z3cform templates
    from zope.pagetemplate.interfaces import IPageTemplate

    component.provideAdapter(
        plone.z3cform.templates.wrapped_form_factory,
        (None, None),
        IPageTemplate,
    )

    from z3c.form.interfaces import IErrorViewSnippet

    component.provideAdapter(
        error.ErrorViewSnippet,
        (None, None, None, None, None, None),
        IErrorViewSnippet,
    )


class P3FLayer(Layer):
    defaultBases = (zope.STARTUP,)

    def setUp(self):
        self['configurationContext'] = context = zca.stackConfigurationContext(
            self.get('configurationContext')
        )
        import plone.z3cform

        xmlconfig.file('testing.zcml', plone.z3cform, context=context)
        import z3c.form

        xmlconfig.file('configure.zcml', z3c.form, context=context)

    def tearDown(self):
        del self['configurationContext']


P3F_FIXTURE = P3FLayer()
FUNCTIONAL_TESTING = zope.FunctionalTesting(
    bases=(P3F_FIXTURE,), name="plone.z3cform:Functional"
)


class Py23DocChecker(doctest.OutputChecker):
    def check_output(self, want, got, optionflags):
        if six.PY2:
            got = re.sub(
                'LocationError', 'zope.location.interfaces.LocationError', got
            )
            got = re.sub("u'(.*?)'", "'\\1'", got)
        return doctest.OutputChecker.check_output(self, want, got, optionflags)


def test_suite():
    layout_txt = layered(
        doctest.DocFileSuite('layout.txt', checker=Py23DocChecker()),
        layer=FUNCTIONAL_TESTING,
    )
    inputs_txt = layered(
        doctest.DocFileSuite('inputs.txt', checker=Py23DocChecker()),
        layer=FUNCTIONAL_TESTING,
    )
    fieldsets_txt = layered(
        doctest.DocFileSuite('fieldsets/README.rst', checker=Py23DocChecker()),
        layer=FUNCTIONAL_TESTING,
    )

    traversal_txt = layered(
        doctest.DocFileSuite('traversal.txt', checker=Py23DocChecker()),
        layer=FUNCTIONAL_TESTING,
    )

    return unittest.TestSuite(
        [
            layout_txt,
            inputs_txt,
            fieldsets_txt,
            traversal_txt,
            doctest.DocFileSuite(
                'crud/README.txt',
                setUp=testing.setUp,
                tearDown=testing.tearDown,
                checker=Py23DocChecker(),
            ),
            doctest.DocTestSuite(
                'plone.z3cform.crud.crud',
                setUp=testing.setUp,
                tearDown=testing.tearDown,
                checker=Py23DocChecker(),
            ),
        ]
    )
