FROM node:20-alpine

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

# Expose Vite default port
EXPOSE 5173

# Run dev server accessible externally
CMD ["npm", "run", "dev", "--", "--host"]
