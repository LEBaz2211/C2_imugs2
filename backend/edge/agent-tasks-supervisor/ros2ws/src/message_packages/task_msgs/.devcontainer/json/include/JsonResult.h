#pragma once

#ifndef JsonResult_h
#define JsonResult_h

#include <optional>
#include <string>

template <class T>
class JsonResult
{
public:
        const std::optional<T> Result;
        const bool Success;
        const std::string Log;

        JsonResult(const T result) : Result(result), Success(true), Log(""){};
        JsonResult(const T result, bool success, std::string log) : Result(result), Success(success), Log(log){};
        JsonResult(const std::string error) : Success(false), Log(error){};
};
#endif
