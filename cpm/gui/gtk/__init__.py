
try:
    import gtk
except ImportError:
    from cpm import Error
    raise Error, "gtk interface not found"
    
