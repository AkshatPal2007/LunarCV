import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests',timeout:180000,workers:1,use:{baseURL:process.env.LUNARCV_URL||'http://127.0.0.1:5173',headless:true,trace:'retain-on-failure'},reporter:[['list'],['html',{open:'never'}]]});
