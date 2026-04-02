# run all the tests in the project
# this is a simple script that runs all the tests in the project
# it is not meant to be a comprehensive test runner, but it is a simple way to
# run all the tests in the project

echo "Running all tests..."
echo "backend tests..."
pytest 

echo "frontend tests..."
node --test frontend/src/components/*.test.js

echo "All tests completed!"

