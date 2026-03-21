from django import template

register = template.Library()

@register.simple_tag
def url_replace(request, field, value):
    """
    Replace a field value in the current GET parameters
    """
    dict_ = request.GET.copy()
    dict_[field] = value
    return dict_.urlencode()