#pragma once

#ifndef Isotime_h
#define Isotime_h

#include <time.h>
#include <stdio.h>
#include <string>
#include <chrono>
#include <sstream>
#include <iomanip>
class Isotime
{
public:
    static time_t FromIso8601(const std::string &date)
    {
        return FromIso8601(date.c_str());
    };

    static time_t FromIso8601(const double &date)
    {
        return FromIso8601(std::to_string(date).c_str());
    };

    static time_t FromIso8601(const char *date)
    {
        struct tm tt = {};
        double seconds;
        if (sscanf(date, "%04d-%02d-%02dT%02d:%02d:%lfZ", &tt.tm_year, &tt.tm_mon, &tt.tm_mday, &tt.tm_hour, &tt.tm_min, &seconds) != 6)
            return -1;
        tt.tm_sec = (int)seconds;
        tt.tm_mon -= 1;
        tt.tm_year -= 1900;
        tt.tm_isdst = -1;
        return mktime(&tt) - timezone;
    };

    static std::string ToIso8601(const time_t date)
    {
        std::ostringstream ss;
        ss << std::put_time(gmtime(&date), "%FT%TZ");
        return ss.str();
    };
};

#endif
