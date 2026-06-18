#include <bits/stdc++.h>
#include <boost/uuid/uuid.hpp>            // uuid class
#include <boost/uuid/uuid_generators.hpp> // generators
#include <boost/uuid/string_generator.hpp>
#include <boost/uuid/uuid_io.hpp>         // streaming operators etc.

#include <unique_identifier_msgs/msg/uuid.hpp>


inline std::vector<uint8_t> convertBoostUuidtoUint8vector(boost::uuids::uuid boost_uuid)
{
	// Convert boost uuid to uint8_t vector (= extracting Bytes)
    std::vector<uint8_t> uint8_vector_from_uuid(boost_uuid.size());
	std::copy(boost_uuid.begin(), boost_uuid.end(), uint8_vector_from_uuid.begin());
    
    return uint8_vector_from_uuid;
}

inline boost::uuids::uuid convertUint8vectortoBoostUuid(std::vector<uint8_t> uint8_vector)
{
	// Convert uint8_t vector to boost uuid
    char char_array_from_uint_vec[16];
    for (int i = 0; i <16; i++) {char_array_from_uint_vec[i] = (char)uint8_vector[i];} // Convert to char array
    boost::uuids::uuid uuid_from_uint8_vector;
    memcpy(&uuid_from_uint8_vector,  char_array_from_uint_vec, 16);
    
    return uuid_from_uint8_vector;
}

inline std::vector<uint8_t> convertStringUuidtoUint8vector(std::string boost_uuid_str)
{
	// Convert string uuid to uint8_t vector (= extracting Bytes)
	std::replace( boost_uuid_str.begin(), boost_uuid_str.end(), '_', '-'); // replace all '_' to '-'
    boost::uuids::string_generator gen;
	boost::uuids::uuid boost_uuid_from_str = gen(boost_uuid_str);
    std::vector<uint8_t> uint8_vector_from_string = convertBoostUuidtoUint8vector(boost_uuid_from_str);
    
    return uint8_vector_from_string;
}


inline std::string convertUint8vectortoStringUuid(std::vector<uint8_t> uint8_vector)
{
	// Convert uint8_t vector to string uuid
    boost::uuids::uuid uuid_from_uint8_vector = convertUint8vectortoBoostUuid(uint8_vector);
    std::string uuid_str = boost::uuids::to_string(uuid_from_uint8_vector);
	// std::replace( uuid_str.begin(), uuid_str.end(), '-', '_'); // replace all '-' to '_'
    
    return uuid_str;
}

inline unique_identifier_msgs::msg::UUID convertStringUuidtoRosUuid(std::string string_uuid)
{
	// Convert string uuid to uint8_t vector 
    std::vector<uint8_t> uint8_vector_from_string = convertStringUuidtoUint8vector(string_uuid);
 
	std::array<uint8_t, 16> arr;
	for (int i = 0; i <= 16; i++) {
        arr[i] = uint8_vector_from_string[i];
    }

	unique_identifier_msgs::msg::UUID ros_uuid;
	ros_uuid.uuid = arr;
    
    
    return ros_uuid;
}

inline std::string convertRosUuidtoStringUuid( unique_identifier_msgs::msg::UUID ros_uuid)
{
    auto uuid = ros_uuid.uuid;
    
    std::vector<uint8_t> uint8_vector(&uuid[0], &uuid[16]);
 
	// Convert  uint8_t vector to string uuid
    std::string string_uuid = convertUint8vectortoStringUuid(uint8_vector);

    return string_uuid;
}


// // Example  Driver code
// int main()
// {	
    
//    // Generate random boost uuid
//    boost::uuids::uuid boost_uuid = boost::uuids::random_generator()();
//    // Convert boost uuid to string
//    std::string boost_uuid_str = boost::uuids::to_string(boost_uuid);
//    std::cout << "random generated boost uuid string = " << boost_uuid_str << std::endl;
    
//    // Convert string to boost uuid
//    boost::uuids::string_generator gen;
//	boost::uuids::uuid boost_uuid_from_str = gen(boost_uuid_str);
	
//    // Convert boost uuid to uint8_t vector (= extracting Bytes)
//    std::vector<uint8_t> uint8_vector_from_uuid = convertBoostUuidtoUint8vector(boost_uuid_from_str);
//    std::cout << "(int) uint8_t elements extracted from uuid = ";
//    for (int i = 0; i <16; i++) {std::cout << (int) uint8_vector_from_uuid[i] << " ";}; std::cout << std::endl;
    
    
//    // Convert uint8_t vector to boost uuid
//    boost::uuids::uuid uuid_from_uint8_vector = convertUint8vectortoBoostUuid(uint8_vector_from_uuid);

//    // Convert boost uuid to string
//    std::string boost_uuid_str_2 = boost::uuids::to_string(uuid_from_uint8_vector);
//    std::cout << "boost uuid string from boost uuid = " << boost_uuid_str_2 << std::endl;
    
//    // Convert uint8_t vector to string uuid
//    std::string boost_uuid_str_from_uint8_vec = convertUint8vectortoStringUuid(uint8_vector_from_uuid);
//    std::cout << "boost uuid string from uint8 vector = " << boost_uuid_str_from_uint8_vec << std::endl;
    
//    // Convert string uuid to uint8_t vector
//    std::vector<uint8_t> uint8_vector_from_string = convertStringUuidtoUint8vector(boost_uuid_str_from_uint8_vec);
//    std::cout << "(int) uint8_t elements extracted from string uuid = ";
//    for (int i = 0; i <16; i++) {std::cout << (int) uint8_vector_from_string[i] << " ";}; std::cout << std::endl;
//
// 	return 0;
// }
