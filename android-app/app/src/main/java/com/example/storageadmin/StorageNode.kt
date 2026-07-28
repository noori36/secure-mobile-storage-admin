package com.example.storageadmin

data class StorageNode(
    val id: String,
    val status: String,
    val disk_usage: Int,
    val latency: Int
)