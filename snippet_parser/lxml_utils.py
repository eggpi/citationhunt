def remove_element(element):
    '''Remove an element from its container element, keeping its tail.'''
    if element.tail:
        if element.getprevious() is not None:
            element.getprevious().tail = (
                element.getprevious().tail or '') + element.tail
        else:
            element.getparent().text = (
                element.getparent().text or '') + element.tail
    element.getparent().remove(element)

def strip_space_before_element(element):
    '''Remove space before an element.'''
    # The text preceding the element is exposed by lxml as either the tail
    # of the "previous" element, or, if there's no previous element, the
    # text of the parent.
    if element.getprevious() is not None:
        if element.getprevious().tail:
            element.getprevious().tail = element.getprevious().tail.rstrip()
    elif element.getparent() is not None and element.getparent().text:
        element.getparent().text = element.getparent().text.rstrip()
