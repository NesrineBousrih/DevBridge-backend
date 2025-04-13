
# Step 1: Clone the repository if not exists
if [ ! -d "$PROJECT_DIR" ]; then
    echo "Cloning Django project template..."
    git clone https://github.com/NesrineBousrih/Django-Init-Automation.git
fi

# Step 2: Navigate into project
cd $PROJECT_DIR

# Step 3: Copy .env.example to .env if it doesn't exist
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    
    # Update .env with app and model information
    # Using printf to ensure newlines are properly added
    printf "\nAPP_NAME=%s\n" "$APP_NAME" >> .env
    printf "MODEL_NAME=%s\n" "$MODEL_NAME" >> .env
    printf "MODEL_FIELDS=\"%s\"\n" "${FIELDS[*]}" >> .env
fi

# Step 4: Start Docker Compose (Postgres + Django)
echo "Starting Docker containers..."
docker-compose up -d --build 

echo "Django app '$APP_NAME' with model '$MODEL_NAME' is being created..."
echo "Added fields: ${FIELDS[*]}"
echo "Access your project at http://localhost:8000"
