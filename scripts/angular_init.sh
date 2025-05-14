# Step 1: Clone the repository if not exists
if [ ! -d "$PROJECT_DIR" ]; then
  echo "Cloning Angular project template..."
  git clone https://github.com/NesrineBousrih/Angular-Init-Automation.git
fi

# Step 2: Navigate into project
cd $PROJECT_DIR

# Step 3: Make sure the scripts directory exists
mkdir -p scripts

# Step 4: Create or update .env file
echo "Creating .env file..."
cat > .env << EOF
APP_NAME=$APP_NAME
MODELS_DATA="$MODELS_DATA"
EOF

# Step 5: Start Docker Compose
echo "Starting Docker containers..."
docker-compose up -d --build

echo "Angular app with CRUD for models is being created..."
echo "Access your project at http://localhost:4200"