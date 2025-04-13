# Convert model name to PascalCase (e.g., product -> Product)
CAP_MODEL_NAME=$(echo "$MODEL_NAME" | awk '{print toupper(substr($0,1,1)) tolower(substr($0,2))}')


# Set project name and extract command line arguments
PROJECT_DIR="Angular-Init-Automation"

# Step 0: Clone the repository if not exists
if [ ! -d "$PROJECT_DIR" ]; then
    echo "Cloning Angular project template..."
    git clone https://github.com/NesrineBousrih/Angular-Init-Automation.git
fi

# Move into the existing template project
cd $PROJECT_DIR || { echo "Error: $PROJECT_DIR project not found"; exit 1; }

# Ensure required directories exist
mkdir -p src/app/models
mkdir -p src/app/services
mkdir -p src/app/pages
mkdir -p src/environments

# Create environment files
cat <<EOF > src/environments/environment.ts
export const environment = {
  production: false,
  apiUrl: 'http://127.0.0.1:8000'
};
EOF

cat <<EOF > src/environments/environment.prod.ts
export const environment = {
  production: true,
  apiUrl: '\${API_URL}'
};
EOF

# Generate typed model with all fields
cat <<EOF > src/app/models/$MODEL_NAME.model.ts
export interface $CAP_MODEL_NAME {
  id?: number;
EOF
for FIELD in $FIELDS; do
  echo "  $FIELD: string;" >> src/app/models/$MODEL_NAME.model.ts
done
echo "}" >> src/app/models/$MODEL_NAME.model.ts

# Generate standalone component for the model
ng generate component pages/$MODEL_NAME --standalone --flat --inline-template --inline-style

# Generate service for the model
ng generate service services/$MODEL_NAME

# Generate standalone HomeComponent (if not already created)
if [ ! -f src/app/pages/home.component.ts ]; then
  ng generate component pages/home --standalone --flat --inline-template --inline-style
fi

# Modify HomeComponent to have an <h1>
cat <<EOF > src/app/pages/home.component.ts
import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule],
  template: \`
  <div class="container mx-auto p-4 text-center">
    <h1 class="text-3xl font-bold">Welcome to the Home Page</h1>
  </div>
  \`
})
export class HomeComponent {}
EOF

# Modify service to use environment variable for API URL
cat <<EOF > src/app/services/$MODEL_NAME.service.ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { $CAP_MODEL_NAME } from '../models/$MODEL_NAME.model';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ${CAP_MODEL_NAME}Service {
  private baseUrl = \`\${environment.apiUrl}/$APP_NAME/$MODEL_NAME\`;

  constructor(private http: HttpClient) {}

  getAll(): Observable<$CAP_MODEL_NAME[]> {
    return this.http.get<$CAP_MODEL_NAME[]>(this.baseUrl);
  }

  getOne(id: number): Observable<$CAP_MODEL_NAME> {
    return this.http.get<$CAP_MODEL_NAME>(\`\${this.baseUrl}/\${id}\`);
  }

  create(data: $CAP_MODEL_NAME): Observable<$CAP_MODEL_NAME> {
    return this.http.post<$CAP_MODEL_NAME>(this.baseUrl+"/", data);
  }

  update(id: number, data: $CAP_MODEL_NAME): Observable<$CAP_MODEL_NAME> {
    return this.http.put<$CAP_MODEL_NAME>(\`\${this.baseUrl}/\${id}/\`, data);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(\`\${this.baseUrl}/\${id}/\`);
  }
}
EOF

# Create an array of fields to correctly pass field names
FIELD_ARRAY="["
for FIELD in $FIELDS; do
  FIELD_ARRAY+="'$FIELD', "
done
FIELD_ARRAY="${FIELD_ARRAY%, }]"

# Modify component to handle full CRUD operations
cat <<EOF > src/app/pages/$MODEL_NAME.component.ts
import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ${CAP_MODEL_NAME}Service } from '../services/$MODEL_NAME.service';
import { $CAP_MODEL_NAME } from '../models/$MODEL_NAME.model';

@Component({
  selector: 'app-$MODEL_NAME',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: \`
  <div class="container mx-auto p-6">
    <h1 class="text-2xl font-bold mb-4">$CAP_MODEL_NAME Management</h1>

    <!-- Form for Adding / Updating -->
    <form (ngSubmit)="save()" class="bg-gray-100 p-4 rounded mb-4">
      <div *ngFor="let field of displayFields">
        <label class="block font-semibold">{{ field }}</label>
        <input [ngModel]="getFormValue(field)" (ngModelChange)="setFormValue(field, \$event)" name="{{field}}" class="w-full p-2 border rounded" required>
      </div>
      <button type="submit" class="mt-3 px-4 py-2 bg-green-500 text-white rounded">
        {{ editing ? 'Update' : 'Add' }} $CAP_MODEL_NAME
      </button>
      <button type="button" *ngIf="editing" (click)="resetForm()" class="ml-2 px-4 py-2 bg-gray-500 text-white rounded">Cancel</button>
    </form>

    <!-- Table of Records -->
    <table class="w-full border-collapse border">
      <thead>
        <tr class="bg-gray-300">
          <th *ngFor="let field of displayFields" class="border p-2">{{ field }}</th>
          <th class="border p-2">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr *ngFor="let item of items">
          <td *ngFor="let field of displayFields" class="border p-2">{{ getItemValue(item, field) }}</td>
          <td class="border p-2">
            <button (click)="edit(item)" class="bg-blue-500 text-white px-2 py-1 rounded">Edit</button>
            <button (click)="deleteItem(item)" class="bg-red-500 text-white px-2 py-1 rounded ml-2">Delete</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
  \`
})
export class ${CAP_MODEL_NAME}Component implements OnInit {
  items: $CAP_MODEL_NAME[] = [];
  // Define fields for the data model
  displayFields: string[] = $FIELD_ARRAY;
  formData: $CAP_MODEL_NAME = {} as $CAP_MODEL_NAME;
  editing = false;
  editId: number | null = null;
  private service = inject(${CAP_MODEL_NAME}Service);

  ngOnInit(): void {
    this.fetchData();
  }

  fetchData(): void {
    this.service.getAll().subscribe(data => this.items = data);
  }

  // Helper methods for type-safe property access
  getFormValue(field: string): string {
    return (this.formData as any)[field] || '';
  }

  setFormValue(field: string, value: string): void {
    (this.formData as any)[field] = value;
  }

  getItemValue(item: $CAP_MODEL_NAME, field: string): string {
    return (item as any)[field] || '';
  }

  save(): void {
    if (this.editing && this.editId !== null) {
      this.service.update(this.editId, this.formData).subscribe(() => {
        this.fetchData();
        this.resetForm();
      });
    } else {
      this.service.create(this.formData).subscribe(() => {
        this.fetchData();
        this.resetForm();
      });
    }
  }

  edit(item: $CAP_MODEL_NAME): void {
    this.formData = { ...item };
    this.editId = item.id !== undefined ? item.id : null;
    this.editing = true;
  }

  deleteItem(item: $CAP_MODEL_NAME): void {
    if (item.id !== undefined) {
      this.service.delete(item.id).subscribe(() => this.fetchData());
    }
  }

  resetForm(): void {
    this.formData = {} as $CAP_MODEL_NAME;
    this.editing = false;
    this.editId = null;
  }
}
EOF

# Ensure app.routes.ts exists
if [ ! -f src/app/app.routes.ts ]; then
  echo "import { Routes } from '@angular/router';" > src/app/app.routes.ts
  echo "export const routes: Routes = [];" >> src/app/app.routes.ts
fi

# Modify routes to include home and the new CRUD page
cat <<EOF > src/app/app.routes.ts
import { Routes } from '@angular/router';
import { HomeComponent } from './pages/home.component';
import { ${CAP_MODEL_NAME}Component } from './pages/$MODEL_NAME.component';

export const routes: Routes = [
  { path: '', redirectTo: 'home', pathMatch: 'full' },
  { path: 'home', component: HomeComponent },
  { path: '$MODEL_NAME', component: ${CAP_MODEL_NAME}Component },
];
EOF

# Install dependencies
echo "Installing dependencies..."
npm install --force or --legacy-peer-deps


# Check if docker-compose.yml exists in  directory
if [ ! -f "docker-compose.yml" ]; then
  echo "Error: docker-compose.yml not found in  directory."
  exit 1
fi

# Validate docker-compose file
echo "Validating docker-compose file..."
if ! docker-compose config; then
  echo "Error: Docker Compose file validation failed."
  exit 1
fi

# Start the application using Docker Compose
echo "Starting the application with Docker Compose..."
docker-compose up -d

# Check if Docker Compose started successfully
if [ $? -eq 0 ]; then
  echo "Application started successfully!"
  echo "Frontend available at: http://localhost:4200"
  echo "Backend available at: http://127.0.0.1:8000"
else
  echo "Error: Failed to start the application with Docker Compose."
  exit 1
fi