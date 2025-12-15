(function_definition
  name: (identifier) @function.name)

(class_definition
  name: (identifier) @class.name)

(import_statement
  name: (dotted_name) @import.name)

(import_from_statement
  module_name: (dotted_name) @import.module)
