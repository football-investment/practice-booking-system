#!/bin/bash
echo "🔍 FRONTEND SETUP VERIFICATION"
echo "=============================="

# Check directory structure
dirs=("src" "public" "src/components" "src/pages" "src/services" "src/contexts")
for dir in "${dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo "✅ Directory exists: $dir"
    else
        echo "❌ Missing directory: $dir"
    fi
done

# Check files
files=("package.json" "public/index.html" "src/index.js" "README.md")
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ File exists: $file"
    else
        echo "❌ Missing file: $file"
    fi
done

echo ""
echo "📋 Next steps:"
echo "1. cd frontend"
echo "2. npm install"
echo "3. npm start"
echo "4. Verify frontend loads at http://localhost:3000"
