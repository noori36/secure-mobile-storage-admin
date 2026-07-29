package com.example.storageadmin

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import android.content.Context
import android.util.Log
import androidx.compose.ui.platform.LocalContext
import android.os.Handler
import android.os.Looper
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            MaterialTheme {
                StorageAdminApp()
            }
        }
    }
}

@Composable
fun StorageAdminApp() {

    var isLoggedIn by remember {
        mutableStateOf(false)
    }

    if (isLoggedIn) {
        DashboardScreen()
    } else {
        LoginScreen(
            onLoginSuccess = {
                isLoggedIn = true
            }
        )
    }
}

private fun getSecurePreferences(context: Context) =
    EncryptedSharedPreferences.create(
        context,
        "secure_admin_preferences",
        MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build(),
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
    )

private fun saveAccessToken(
    context: Context,
    token: String
) {
    getSecurePreferences(context)
        .edit()
        .putString("access_token", token)
        .apply()
}

@Composable
fun LoginScreen(
    onLoginSuccess: () -> Unit
) {

    var username by remember {
        mutableStateOf("")
    }

    var password by remember {
        mutableStateOf("")
    }

    var message by remember {
        mutableStateOf("")
    }

    val context = LocalContext.current

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(32.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {

        Text(
            text = "Storage Admin",
            style = MaterialTheme.typography.headlineMedium
        )

        Spacer(
            modifier = Modifier.height(30.dp)
        )

        OutlinedTextField(
            value = username,
            onValueChange = {
                username = it
            },
            label = {
                Text("Username")
            },
            singleLine = true,
            modifier = Modifier.fillMaxWidth()
        )

        Spacer(
            modifier = Modifier.height(16.dp)
        )

        OutlinedTextField(
            value = password,
            onValueChange = {
                password = it
            },
            label = {
                Text("Password")
            },
            singleLine = true,
            visualTransformation =
                PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(
                keyboardType = KeyboardType.Password
            ),
            modifier = Modifier.fillMaxWidth()
        )

        Spacer(
            modifier = Modifier.height(24.dp)
        )

        Button(
            onClick = {

                message = "Logging in..."

                val request = LoginRequest(
                    username = username,
                    password = password
                )

                RetrofitClient.api
                    .login(request)
                    .enqueue(
                        object : Callback<LoginResponse> {

                            override fun onResponse(
                                call: Call<LoginResponse>,
                                response: Response<LoginResponse>
                            ) {

                                if (response.isSuccessful) {

                                    val token = response.body()?.access_token

                                    if (token != null) {

                                        // secure storage
                                        val sharedPreferences =
                                            saveAccessToken(
                                                context = context,
                                                token = token
                                            )
                                    }

                                    message = "Login successful"
                                    onLoginSuccess()
                                } else {

                                    message =
                                        "Invalid username or password"
                                }
                            }

                            override fun onFailure(
                                call: Call<LoginResponse>,
                                t: Throwable
                            ) {

                                message =
                                    "Connection failed: ${t.message}"
                            }
                        }
                    )
            },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("LOGIN")
        }

        Spacer(
            modifier = Modifier.height(16.dp)
        )

        Text(message)
    }
}

@Composable
fun DashboardScreen() {

    var nodes by remember {
        mutableStateOf<List<StorageNode>>(emptyList())
    }

    var isLoading by remember {
        mutableStateOf(true)
    }

    var errorMessage by remember {
        mutableStateOf("")
    }

    fun loadNodes() {

        isLoading = true
        errorMessage = ""

        RetrofitClient.api
            .getNodes()
            .enqueue(
                object : Callback<List<StorageNode>> {

                    override fun onResponse(
                        call: Call<List<StorageNode>>,
                        response: Response<List<StorageNode>>
                    ) {

                        if (response.isSuccessful) {

                            nodes =
                                response.body() ?: emptyList()

                            errorMessage = ""

                        } else {

                            errorMessage =
                                "Could not load storage nodes"
                        }

                        isLoading = false
                    }

                    override fun onFailure(
                        call: Call<List<StorageNode>>,
                        t: Throwable
                    ) {

                        errorMessage =
                            "Connection failed: ${t.message}"

                        isLoading = false
                    }
                }
            )
    }

    LaunchedEffect(Unit) {
        loadNodes()
    }

    val onlineCount = nodes.count {
        it.status.equals(
            "online",
            ignoreCase = true
        )
    }

    val degradedCount = nodes.count {
        it.status.equals(
            "degraded",
            ignoreCase = true
        )
    }

    val disabledCount = nodes.count {
        it.status.equals(
            "disabled",
            ignoreCase = true)
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp)
    ) {

        Text(
            text = "Dashboard",
            style = MaterialTheme.typography.headlineMedium
        )

        Spacer(
            modifier = Modifier.height(24.dp)
        )

        if (isLoading) {

            CircularProgressIndicator()

        } else if (errorMessage.isNotEmpty()) {

            Text(errorMessage)

        } else {

            Text(
                text = "Total Nodes: ${nodes.size}",
                style = MaterialTheme.typography.titleMedium
            )

            Text(
                text = "Online: $onlineCount"
            )

            Text(
                text = "Degraded: $degradedCount"
            )

            Text(
                text = "Disabled: $disabledCount"
            )

            Spacer(
                modifier = Modifier.height(24.dp)
            )

            LazyColumn(
                verticalArrangement =
                    Arrangement.spacedBy(12.dp)
            ) {

                items(nodes) { node ->

                    NodeCard(
                        node = node,
                        onDisableClick = {

                            disableNode(
                                nodeId = node.id,
                                onSuccess = {
                                    loadNodes()
                                },
                                onError = { error ->
                                    errorMessage = error
                                }
                            )
                        },
                        onEnableClick = {

                            enableNode(
                                nodeId = node.id,
                                onSuccess = {

                                    Handler(
                                        Looper.getMainLooper()
                                    ).postDelayed(
                                        {
                                            loadNodes()
                                        },
                                        3000
                                    )
                                },
                                onError = { error ->
                                    errorMessage = error
                                }
                            )
                        }
                    )
                }
            }
        }
    }
}

@Composable
fun NodeCard(
    node: StorageNode,
    onDisableClick: () -> Unit,
    onEnableClick: () -> Unit
) {

    Card(
        modifier = Modifier.fillMaxWidth()
    ) {

        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
        ) {

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement =
                    Arrangement.SpaceBetween,
                verticalAlignment =
                    Alignment.CenterVertically
            ) {

                Column {

                    Text(
                        text = node.id,
                        style =
                            MaterialTheme.typography.titleMedium
                    )

                    Text(
                        text =
                            "Disk usage: ${node.disk_usage}%"
                    )

                    Text(
                        text =
                            "Latency: ${node.latency} ms"
                    )
                }

                Text(
                    text = node.status.replaceFirstChar {
                        it.uppercase()
                    }
                )
            }

            Spacer(
                modifier = Modifier.height(12.dp)
            )

            if (
                node.status.equals(
                    "disabled",
                    ignoreCase = true
                )
            ) {

                Button(
                    onClick = onEnableClick,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Enable Node")
                }

            } else {

                Button(
                    onClick = onDisableClick,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Disable Node")
                }
            }
        }
    }
}

private fun disableNode(
    nodeId: String,
    onSuccess: () -> Unit,
    onError: (String) -> Unit
) {

    RetrofitClient.api
        .disableNode(nodeId)
        .enqueue(
            object : Callback<Map<String, Any>> {

                override fun onResponse(
                    call: Call<Map<String, Any>>,
                    response: Response<Map<String, Any>>
                ) {

                    if (response.isSuccessful) {

                        onSuccess()

                    } else {

                        onError(
                            "Could not disable $nodeId. " +
                                    "Error: ${response.code()}"
                        )
                    }
                }

                override fun onFailure(
                    call: Call<Map<String, Any>>,
                    t: Throwable
                ) {

                    onError(
                        "Disable request failed: ${t.message}"
                    )

                    Log.e(
                        "StorageAdmin",
                        "Could not disable $nodeId",
                        t
                    )
                }
            }
        )
}

private fun enableNode(
    nodeId: String,
    onSuccess: () -> Unit,
    onError: (String) -> Unit
) {

    RetrofitClient.api
        .enableNode(nodeId)
        .enqueue(
            object : Callback<Map<String, Any>> {

                override fun onResponse(
                    call: Call<Map<String, Any>>,
                    response: Response<Map<String, Any>>
                ) {

                    if (response.isSuccessful) {

                        onSuccess()

                    } else {

                        onError(
                            "Could not enable $nodeId. " +
                                    "Error: ${response.code()}"
                        )
                    }
                }

                override fun onFailure(
                    call: Call<Map<String, Any>>,
                    t: Throwable
                ) {

                    onError(
                        "Enable request failed: ${t.message}"
                    )

                    Log.e(
                        "StorageAdmin",
                        "Could not enable $nodeId",
                        t
                    )
                }
            }
        )
}