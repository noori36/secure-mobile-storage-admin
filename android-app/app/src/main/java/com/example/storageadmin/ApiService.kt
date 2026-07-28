package com.example.storageadmin

import retrofit2.Call
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

interface ApiService {

    @POST("login")
    fun login(
        @Body request: LoginRequest
    ): Call<LoginResponse>

    @GET("nodes")
    fun getNodes(): Call<List<StorageNode>>

    @POST("nodes/{nodeId}/disable")
    fun disableNode(
        @Path("nodeId") nodeId: String
    ): Call<Map<String, Any>>

    @POST("nodes/{nodeId}/enable")
    fun enableNode(
        @Path("nodeId") nodeId: String
    ): Call<Map<String, Any>>
}