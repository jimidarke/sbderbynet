# License Update Instructions

This document provides instructions for updating license headers across the DerbyNet codebase.

## License Files

The following license files are available in the repository:

1. `MIT-LICENSE.txt` - The main license file for the project
2. `LICENSE_HEADER.txt` - License header for PHP, JavaScript, CSS, and other files
3. `LICENSE_HEADER_PYTHON.txt` - License header for Python files
4. `extras/soapbox/LICENSE.txt` - License file for the Soapbox Derby extension

## Adding License Headers to New Files

All new files should include the appropriate license header:

### For Python files:

```python
'''
Copyright (c) 2025 DerbyNet Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''
```

### For PHP, JavaScript, CSS, and other files:

```php
/*
 * Copyright (c) 2025 DerbyNet Contributors
 * 
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 * 
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 * 
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */
```

## Updating Existing Files

To update license headers in existing files, follow these steps:

### For Python files:

1. Check if the file already has a license header
2. If it does, replace it with the content from `LICENSE_HEADER_PYTHON.txt`
3. If it doesn't, add the content from `LICENSE_HEADER_PYTHON.txt` at the top of the file, after any existing docstrings or descriptions

### For PHP, JavaScript, CSS, and other files:

1. Check if the file already has a license header
2. If it does, replace it with the content from `LICENSE_HEADER.txt`
3. If it doesn't, add the content from `LICENSE_HEADER.txt` at the top of the file, after any opening tags

## Automated License Updates

You can use the following script to add license headers to multiple files at once:

```bash
#!/bin/bash
# Script to add license headers to files

# Get the license headers
PYTHON_HEADER=$(cat LICENSE_HEADER_PYTHON.txt)
GENERAL_HEADER=$(cat LICENSE_HEADER.txt)

# Function to add header to Python files
add_python_header() {
  local file=$1
  if ! grep -q "Copyright (c)" "$file"; then
    echo "$PYTHON_HEADER" > "$file.new"
    cat "$file" >> "$file.new"
    mv "$file.new" "$file"
    echo "Added header to $file"
  fi
}

# Function to add header to other files
add_general_header() {
  local file=$1
  if ! grep -q "Copyright (c)" "$file"; then
    echo "$GENERAL_HEADER" > "$file.new"
    cat "$file" >> "$file.new"
    mv "$file.new" "$file"
    echo "Added header to $file"
  fi
}

# Process Python files
find . -name "*.py" -type f | while read -r file; do
  add_python_header "$file"
done

# Process PHP files
find . -name "*.php" -type f | while read -r file; do
  add_general_header "$file"
done

# Process JavaScript files
find . -name "*.js" -type f | while read -r file; do
  add_general_header "$file"
done

# Process CSS files
find . -name "*.css" -type f | while read -r file; do
  add_general_header "$file"
done

echo "License headers have been updated."
```

## License Information in README Files

Make sure all README.md files include the correct license information:

```markdown
## License

This project is open source and released under the MIT License. See the [LICENSE.txt](LICENSE.txt) file for details.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```