from node:22-alpine as deps
workdir /app
copy package*.json ./
run npm ci

from node:22-alpine as builder
workdir /app
copy --from=deps /app/node_modules ./node_modules
copy . .
run npm run build

from node:22-alpine as runner
workdir /app
env NODE_ENV=production
copy --from=builder /app/.next ./.next
copy --from=builder /app/node_modules ./node_modules
copy --from=builder /app/package.json ./package.json
copy --from=builder /app/public ./public
expose 3000
cmd ["npm", "start"]
